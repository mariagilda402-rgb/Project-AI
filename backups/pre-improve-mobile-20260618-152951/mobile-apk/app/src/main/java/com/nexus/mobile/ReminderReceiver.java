package com.nexus.mobile;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;

import androidx.core.app.NotificationCompat;

public class ReminderReceiver extends BroadcastReceiver {

    public static final String EXTRA_TITLE = "reminder_title";
    public static final String EXTRA_BODY = "reminder_body";
    public static final String EXTRA_ID = "reminder_id";
    public static final String EXTRA_IS_ALARM = "reminder_is_alarm";
    public static final String EXTRA_SNOOZE_MINUTES = "reminder_snooze_minutes";
    public static final String EXTRA_MAX_SNOOZE = "reminder_max_snooze";
    public static final String EXTRA_SNOOZE_COUNT = "reminder_snooze_count";

    private static final String CHANNEL_REMINDER = "nexus_reminder_channel";
    private static final String CHANNEL_ALARM = "nexus_alarm_channel";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null) return;

        String title = intent.getStringExtra(EXTRA_TITLE);
        String body = intent.getStringExtra(EXTRA_BODY);
        int id = intent.getIntExtra(EXTRA_ID, 0);
        boolean isAlarm = intent.getBooleanExtra(EXTRA_IS_ALARM, false);

        if (title == null) title = "Nexus";
        if (body == null) body = "";

        if (isAlarm) {
            Intent ringIntent = new Intent(context, AlarmRingActivity.class);
            ringIntent.putExtra(EXTRA_ID, id);
            ringIntent.putExtra(EXTRA_TITLE, title);
            ringIntent.putExtra(EXTRA_BODY, body);
            ringIntent.putExtra(EXTRA_SNOOZE_MINUTES, intent.getIntExtra(EXTRA_SNOOZE_MINUTES, 5));
            ringIntent.putExtra(EXTRA_MAX_SNOOZE, intent.getIntExtra(EXTRA_MAX_SNOOZE, 3));
            ringIntent.putExtra(EXTRA_SNOOZE_COUNT, intent.getIntExtra(EXTRA_SNOOZE_COUNT, 0));
            ringIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);

            PendingIntent fullScreen = PendingIntent.getActivity(
                context,
                id,
                ringIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
            );

            context.startActivity(ringIntent);
            showNotification(context, id, title, body, fullScreen, true);
        } else {
            Intent launchIntent = new Intent(context, MainActivity.class);
            launchIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
            PendingIntent pending = PendingIntent.getActivity(
                context,
                id,
                launchIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
            );
            showNotification(context, id, title, body, pending, false);
        }
    }

    private void showNotification(Context context, int id, String title, String body,
                                  PendingIntent contentIntent, boolean isAlarm) {
        NotificationManager nm = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm == null) return;

        String channelId = isAlarm ? CHANNEL_ALARM : CHANNEL_REMINDER;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                channelId,
                isAlarm ? "Nexus Alarmes" : "Nexus Lembretes",
                NotificationManager.IMPORTANCE_HIGH
            );
            channel.enableVibration(true);
            channel.setBypassDnd(true);
            if (isAlarm) {
                channel.setLockscreenVisibility(NotificationCompat.VISIBILITY_PUBLIC);
            }
            nm.createNotificationChannel(channel);
        }

        NotificationCompat.Builder builder = new NotificationCompat.Builder(context, channelId)
            .setContentTitle(title)
            .setContentText(body)
            .setSmallIcon(android.R.drawable.ic_lock_idle_alarm)
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(isAlarm ? NotificationCompat.CATEGORY_ALARM : NotificationCompat.CATEGORY_REMINDER)
            .setAutoCancel(true)
            .setContentIntent(contentIntent)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC);

        if (isAlarm && Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            builder.setFullScreenIntent(contentIntent, true);
        }

        nm.notify(id, builder.build());
    }
}
