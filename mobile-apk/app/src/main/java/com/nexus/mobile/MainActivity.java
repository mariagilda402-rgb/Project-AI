package com.nexus.mobile;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.ProgressBar;
import android.widget.Toast;

import android.content.Intent;
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
    }

    private void configureWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
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

        webView.addJavascriptInterface(new NexusAndroidBridge(), "NexusAndroid");

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return false;
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
            return "{\"nativeShell\":true,\"platform\":\"android\",\"version\":\"1.0\"}";
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
}
