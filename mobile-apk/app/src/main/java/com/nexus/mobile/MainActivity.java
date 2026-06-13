package com.nexus.mobile;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;

import android.provider.MediaStore;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.util.Base64;
import java.io.ByteArrayOutputStream;

import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.ProgressBar;
import android.widget.Toast;

import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;

import android.content.Intent;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import androidx.core.content.FileProvider;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.List;

public class MainActivity extends Activity {

    private static final int PERMISSION_REQUEST_CODE = 4401;

    private static final int REQUEST_IMAGE_CAPTURE = 4403;
    private String currentPhotoPath = "";

    private static final String LOCAL_APP_URL = "file:///android_asset/index.html";
    private static final String REMOTE_BUNDLE_BASE = "https://mariagilda402-rgb.github.io/Project-AI/mobile/";
    private static final String BUNDLE_DIR_NAME = "mobile_bundle";
    private static final String[] WEB_BUNDLE_FILES = {
        "version.json",
        "index.html",
        "style.css",
        "app.js",
        "manifest.json",
        "sw.js"
    };

    private WebView webView;
    private ProgressBar progressBar;

    @SuppressLint({"SetJavaScriptEnabled", "AddJavascriptInterface"})
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        android.content.SharedPreferences prefs = getSharedPreferences("NexusMobilePrefs", MODE_PRIVATE);
        int lastVersionCode = prefs.getInt("lastVersionCode", -1);
        int currentVersionCode = 1;
        try {
            currentVersionCode = getPackageManager().getPackageInfo(getPackageName(), 0).versionCode;
        } catch (Exception e) {}
        
        if (currentVersionCode > lastVersionCode) {
            deleteRecursively(getDownloadedBundleDir());
            prefs.edit().putInt("lastVersionCode", currentVersionCode).apply();
        }

        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setFlags(
            WindowManager.LayoutParams.FLAG_FULLSCREEN,
            WindowManager.LayoutParams.FLAG_FULLSCREEN
        );

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            getWindow().setStatusBarColor(Color.parseColor("#0d0d12"));
            getWindow().setNavigationBarColor(Color.parseColor("#0d0d12"));
        }

        setContentView(R.layout.activity_main);

        webView = findViewById(R.id.webView);
        progressBar = findViewById(R.id.progressBar);

        configureWebView();
        maybeRequestRuntimePermissions();

        webView.setBackgroundColor(Color.parseColor("#0d0d12"));
        loadBestAvailableApp();
        handleOAuthIntent(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleOAuthIntent(intent);
    }

    private void handleOAuthIntent(Intent intent) {
        if (intent == null || intent.getData() == null || webView == null) {
            return;
        }
        Uri uri = intent.getData();
        if (!"com.nexus.mobile".equals(uri.getScheme()) || !"auth".equals(uri.getHost())) {
            return;
        }
        final String callbackUrl = uri.toString();
        webView.post(() -> {
            String escaped = callbackUrl
                .replace("\\", "\\\\")
                .replace("'", "\\'")
                .replace("\n", "")
                .replace("\r", "");
            webView.evaluateJavascript(
                "if(window.handleOAuthCallback){window.handleOAuthCallback('" + escaped + "');}",
                null
            );
        });
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_IMAGE_CAPTURE && resultCode == RESULT_OK && data != null) {
            android.os.Bundle extras = data.getExtras();
            if (extras != null) {
                Bitmap imageBitmap = (Bitmap) extras.get("data");
                if (imageBitmap != null) {
                    ByteArrayOutputStream stream = new ByteArrayOutputStream();
                    imageBitmap.compress(Bitmap.CompressFormat.JPEG, 80, stream);
                    String base64 = Base64.encodeToString(stream.toByteArray(), Base64.NO_WRAP);
                    String js = "javascript:if(window.onNativeCameraResult) window.onNativeCameraResult('data:image/jpeg;base64," + base64 + "');";
                    webView.evaluateJavascript(js, null);
                }
            }
        }
    }

    private void configureWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        webView.addJavascriptInterface(new NexusAndroidBridge(), "NexusAndroid");
        webView.addJavascriptInterface(new WebAppInterface(), "AndroidNative");
        settings.setDefaultTextEncodingName("utf-8");
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setAllowFileAccess(true);
        settings.setAllowFileAccessFromFileURLs(true);
        settings.setAllowUniversalAccessFromFileURLs(true);
        settings.setAllowContentAccess(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        settings.setDatabaseEnabled(true);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);

        CookieManager cookieManager = CookieManager.getInstance();
        cookieManager.setAcceptCookie(true);
        cookieManager.setAcceptThirdPartyCookies(webView, true);

        settings.setDomStorageEnabled(true);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return false;
            }

            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                if (request != null && request.getUrl() != null) {
                    String host = request.getUrl().getHost();
                    if (host != null && (host.contains("youtube.com") || host.contains("youtu.be") || host.contains("googlevideo.com"))) {
                        try {
                            URL url = new URL(request.getUrl().toString());
                            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
                            connection.setRequestProperty("Referer", "https://www.youtube.com/");
                            connection.setRequestProperty("Origin", "https://www.youtube.com");
                            connection.connect();
                            String contentType = connection.getContentType();
                            if (contentType == null) contentType = "text/html";
                            return new WebResourceResponse(
                                contentType,
                                connection.getContentEncoding() != null ? connection.getContentEncoding() : "utf-8",
                                connection.getInputStream()
                            );
                        } catch (Exception ignored) {
                            // Fall through to default WebView handling
                        }
                    }
                }
                return super.shouldInterceptRequest(view, request);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                progressBar.setVisibility(View.GONE);
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                progressBar.setProgress(newProgress);
                progressBar.setVisibility(newProgress == 100 ? View.GONE : View.VISIBLE);
            }

            @Override
            public void onPermissionRequest(PermissionRequest request) {
                runOnUiThread(() -> {
                    if (hasRuntimePermissionsFor(request.getResources())) {
                        request.grant(request.getResources());
                    } else {
                        maybeRequestRuntimePermissions();
                        request.deny();
                    }
                });
            }
        });
    }

    private void loadBestAvailableApp() {
        File downloadedIndex = getDownloadedBundleIndex();
        if (downloadedIndex.exists()) {
            webView.loadUrl(Uri.fromFile(downloadedIndex).toString());
            return;
        }
        webView.loadUrl(LOCAL_APP_URL);
    }

    private File getDownloadedBundleDir() {
        return new File(getFilesDir(), BUNDLE_DIR_NAME);
    }

    private File getDownloadedBundleIndex() {
        return new File(getDownloadedBundleDir(), "index.html");
    }

    private void maybeRequestRuntimePermissions() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) {
            return;
        }

        List<String> missing = new ArrayList<>();
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            missing.add(Manifest.permission.RECORD_AUDIO);
        }
        if (checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            missing.add(Manifest.permission.CAMERA);
        }
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            missing.add(Manifest.permission.ACCESS_FINE_LOCATION);
        }
        if (checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            missing.add(Manifest.permission.ACCESS_COARSE_LOCATION);
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                missing.add(Manifest.permission.POST_NOTIFICATIONS);
            }
        }

        if (!missing.isEmpty()) {
            requestPermissions(missing.toArray(new String[0]), PERMISSION_REQUEST_CODE);
        }
    }

    private boolean hasRuntimePermissionsFor(String[] webResources) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) {
            return true;
        }

        for (String resource : webResources) {
            if (PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(resource)
                && checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                return false;
            }
            if (PermissionRequest.RESOURCE_VIDEO_CAPTURE.equals(resource)
                && checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
                return false;
            }
        }
        return true;
    }

    private void installWebBundleUpdate() {
        File targetDir = getDownloadedBundleDir();
        File stagingDir = new File(getFilesDir(), BUNDLE_DIR_NAME + "_next");

        try {
            deleteRecursively(stagingDir);
            if (!stagingDir.mkdirs() && !stagingDir.exists()) {
                throw new IOException("Could not create staging bundle directory.");
            }

            for (String fileName : WEB_BUNDLE_FILES) {
                downloadToFile(REMOTE_BUNDLE_BASE + fileName, new File(stagingDir, fileName));
            }

            if (!new File(stagingDir, "index.html").exists()) {
                throw new IOException("Downloaded bundle does not contain index.html.");
            }

            deleteRecursively(targetDir);
            if (!stagingDir.renameTo(targetDir)) {
                throw new IOException("Could not activate downloaded bundle.");
            }

            runOnUiThread(() -> {
                Toast.makeText(this, "Nexus atualizado.", Toast.LENGTH_SHORT).show();
                loadBestAvailableApp();
            });
        } catch (Exception error) {
            deleteRecursively(stagingDir);
            runOnUiThread(() -> Toast.makeText(
                this,
                "Falha ao atualizar: " + error.getMessage(),
                Toast.LENGTH_LONG
            ).show());
        }
    }

    private void downloadToFile(String sourceUrl, File destination) throws IOException {
        URL url = new URL(sourceUrl);
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        connection.setConnectTimeout(15000);
        connection.setReadTimeout(20000);
        connection.setInstanceFollowRedirects(true);

        try {
            int status = connection.getResponseCode();
            if (status < 200 || status >= 300) {
                throw new IOException("HTTP " + status + " for " + sourceUrl);
            }

            File parent = destination.getParentFile();
            if (parent != null && !parent.exists() && !parent.mkdirs()) {
                throw new IOException("Could not create directory for " + destination.getName());
            }

            try (InputStream input = connection.getInputStream();
                 FileOutputStream output = new FileOutputStream(destination)) {
                byte[] buffer = new byte[8192];
                int bytesRead;
                while ((bytesRead = input.read(buffer)) != -1) {
                    output.write(buffer, 0, bytesRead);
                }
            }
        } finally {
            connection.disconnect();
        }
    }

    private void deleteRecursively(File file) {
        if (file == null || !file.exists()) {
            return;
        }
        if (file.isDirectory()) {
            File[] children = file.listFiles();
            if (children != null) {
                for (File child : children) {
                    deleteRecursively(child);
                }
            }
        }
        file.delete();
    }

    public class NexusAndroidBridge {
        @JavascriptInterface
        public String getShellInfo() {
            return "{\"nativeShell\":true,\"platform\":\"android\",\"version\":\"1.2\"}";
        }

        @JavascriptInterface
        public String getOAuthRedirect() {
            return "com.nexus.mobile://auth/callback";
        }

        @JavascriptInterface
        public void openOAuthUrl(String url) {
            runOnUiThread(() -> {
                try {
                    Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                    startActivity(intent);
                } catch (Exception e) {
                    Toast.makeText(MainActivity.this, "Não foi possível abrir login: " + e.getMessage(), Toast.LENGTH_LONG).show();
                }
            });
        }

        @JavascriptInterface
        public void installWebUpdate() {
            new Thread(() -> installWebBundleUpdate()).start();
        }

        @JavascriptInterface
        public void reloadLocalBundle() {
            runOnUiThread(() -> {
                deleteRecursively(getDownloadedBundleDir());
                webView.loadUrl(LOCAL_APP_URL);
            });
        }

        @JavascriptInterface
        public void installNativeApk(String url) {
            new Thread(() -> downloadAndInstallNativeApk(url)).start();
        }
    }

    private void downloadAndInstallNativeApk(String apkUrl) {
        runOnUiThread(() -> {
            progressBar.setProgress(0);
            progressBar.setVisibility(View.VISIBLE);
            Toast.makeText(this, "Baixando atualização do APK...", Toast.LENGTH_SHORT).show();
        });

        File updateDir = new File(getExternalFilesDir(null), "updates");
        if (!updateDir.exists() && !updateDir.mkdirs()) {
            runOnUiThread(() -> Toast.makeText(this, "Erro ao criar pasta de atualização", Toast.LENGTH_LONG).show());
            return;
        }

        File apkFile = new File(updateDir, "update.apk");
        if (apkFile.exists()) {
            apkFile.delete();
        }

        try {
            downloadToFile(apkUrl, apkFile);

            Uri apkUri = FileProvider.getUriForFile(
                this,
                getApplicationContext().getPackageName() + ".fileprovider",
                apkFile
            );

            Intent intent = new Intent(Intent.ACTION_VIEW);
            intent.setDataAndType(apkUri, "application/vnd.android.package-archive");
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(intent);

        } catch (Exception e) {
            e.printStackTrace();
            runOnUiThread(() -> Toast.makeText(this, "Falha ao instalar APK: " + e.getMessage(), Toast.LENGTH_LONG).show());
        } finally {
            runOnUiThread(() -> progressBar.setVisibility(View.GONE));
        }
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    private class WebAppInterface {
        @JavascriptInterface
        public boolean isWifiConnected() {
            try {
                ConnectivityManager cm = (ConnectivityManager) getSystemService(CONNECTIVITY_SERVICE);
                if (cm == null) return false;
                Network network = cm.getActiveNetwork();
                if (network == null) return false;
                NetworkCapabilities caps = cm.getNetworkCapabilities(network);
                if (caps == null) return false;
                return caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)
                    || caps.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET);
            } catch (Exception e) {
                return false;
            }
        }

        @JavascriptInterface
        public boolean isNetworkOnline() {
            try {
                ConnectivityManager cm = (ConnectivityManager) getSystemService(CONNECTIVITY_SERVICE);
                if (cm == null) return false;
                Network network = cm.getActiveNetwork();
                if (network == null) return false;
                NetworkCapabilities caps = cm.getNetworkCapabilities(network);
                return caps != null && caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET);
            } catch (Exception e) {
                return false;
            }
        }

        @JavascriptInterface
        public void startJarvisCall() {
            if (!isWifiConnected()) {
                runOnUiThread(() -> Toast.makeText(MainActivity.this,
                    "Conecte-se ao Wi-Fi para ligar ao Jarvis.", Toast.LENGTH_LONG).show());
                return;
            }
            runOnUiThread(() -> {
                Intent serviceIntent = new Intent(MainActivity.this, JarvisCallService.class);
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    startForegroundService(serviceIntent);
                } else {
                    startService(serviceIntent);
                }
            });
        }

        @JavascriptInterface
        public void scheduleReminder(int id, String title, String body, long triggerAtMs) {
            runOnUiThread(() -> {
                try {
                    AlarmManager alarmManager = (AlarmManager) getSystemService(ALARM_SERVICE);
                    if (alarmManager == null) return;

                    Intent intent = new Intent(MainActivity.this, ReminderReceiver.class);
                    intent.putExtra(ReminderReceiver.EXTRA_ID, id);
                    intent.putExtra(ReminderReceiver.EXTRA_TITLE, title);
                    intent.putExtra(ReminderReceiver.EXTRA_BODY, body);

                    PendingIntent pending = PendingIntent.getBroadcast(
                        MainActivity.this,
                        id,
                        intent,
                        PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
                    );

                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                        alarmManager.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAtMs, pending);
                    } else {
                        alarmManager.setExact(AlarmManager.RTC_WAKEUP, triggerAtMs, pending);
                    }
                } catch (Exception e) {
                    Toast.makeText(MainActivity.this, "Falha ao agendar lembrete", Toast.LENGTH_SHORT).show();
                }
            });
        }

        @JavascriptInterface
        public void cancelReminder(int id) {
            runOnUiThread(() -> {
                try {
                    AlarmManager alarmManager = (AlarmManager) getSystemService(ALARM_SERVICE);
                    if (alarmManager == null) return;

                    Intent intent = new Intent(MainActivity.this, ReminderReceiver.class);
                    PendingIntent pending = PendingIntent.getBroadcast(
                        MainActivity.this,
                        id,
                        intent,
                        PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
                    );
                    alarmManager.cancel(pending);
                } catch (Exception ignored) {
                }
            });
        }

        @JavascriptInterface
        public void showNotification(String title, String message) {
            runOnUiThread(() -> {
                String channelId = "nexus_alert_channel";
                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                    NotificationChannel channel = new NotificationChannel(channelId, "Nexus Alerts", NotificationManager.IMPORTANCE_HIGH);
                    NotificationManager nm = (NotificationManager) getSystemService(android.content.Context.NOTIFICATION_SERVICE);
                    if (nm != null) nm.createNotificationChannel(channel);
                }
                android.app.Notification notif = new androidx.core.app.NotificationCompat.Builder(MainActivity.this, channelId)
                    .setContentTitle(title)
                    .setContentText(message)
                    .setSmallIcon(android.R.drawable.ic_dialog_info)
                    .setPriority(androidx.core.app.NotificationCompat.PRIORITY_HIGH)
                    .build();
                NotificationManager nm = (NotificationManager) getSystemService(android.content.Context.NOTIFICATION_SERVICE);
                if (nm != null) nm.notify((int)(System.currentTimeMillis() % 10000), notif);
            });
        }

        @JavascriptInterface
        public void openNativeCamera() {
            runOnUiThread(() -> {
                Intent takePictureIntent = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
                if (takePictureIntent.resolveActivity(getPackageManager()) != null) {
                    startActivityForResult(takePictureIntent, REQUEST_IMAGE_CAPTURE);
                } else {
                    Toast.makeText(MainActivity.this, "Câmera não encontrada", Toast.LENGTH_SHORT).show();
                }
            });
        }

        @JavascriptInterface
        public void stopJarvisCall() {
            runOnUiThread(() -> {
                Intent serviceIntent = new Intent(MainActivity.this, JarvisCallService.class);
                serviceIntent.setAction("STOP_SERVICE");
                startService(serviceIntent);
            });
        }

        @JavascriptInterface
        public void captureScreenAndClipboard() {
            runOnUiThread(() -> {
                // Clipboard reading
                android.content.ClipboardManager clipboard = (android.content.ClipboardManager) getSystemService(android.content.Context.CLIPBOARD_SERVICE);
                String clipText = "";
                if (clipboard != null && clipboard.hasPrimaryClip() && clipboard.getPrimaryClip().getItemCount() > 0) {
                    CharSequence text = clipboard.getPrimaryClip().getItemAt(0).getText();
                    if(text != null) clipText = text.toString();
                }
                
                // Screen Capture (Simplified mock for now to avoid MediaProjection complexities in background)
                // In a real app, MediaProjection requires user consent Intent onActivityResult.
                String finalClip = clipText;
                
                // Send back to JS
                String jsCode = "javascript:if(window.receiveNativeVision) window.receiveNativeVision('Clipboard: " + finalClip.replace("'", "\\'") + "');";
                webView.evaluateJavascript(jsCode, null);
            });
        }
    }

}
