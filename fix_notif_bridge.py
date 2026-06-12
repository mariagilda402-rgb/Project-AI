path = 'mobile-apk/app/src/main/java/com/nexus/mobile/MainActivity.java'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# Add notification import
if 'import android.app.NotificationManager;' not in c:
    c = c.replace('import android.app.Service;', 'import android.app.Service;\nimport android.app.NotificationManager;\nimport android.app.NotificationChannel;\nimport androidx.core.app.NotificationCompat;')

# Add showNotification method to WebAppInterface
method = '''
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
'''

if 'showNotification' not in c:
    c = c.replace('public void openNativeCamera() {', method + '\n        public void openNativeCamera() {')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("showNotification added to MainActivity")
else:
    print("showNotification already present")
