package com.nexus.mobile;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Persists and reschedules exact alarms so they survive app close and device reboot.
 */
public final class AlarmScheduler {

    private static final String PREFS = "nexus_alarm_prefs";
    private static final String KEY_ALARMS = "alarms_json";

    private AlarmScheduler() {}

    public static void schedule(
        Context context,
        int id,
        String title,
        String body,
        long triggerAtMs,
        boolean isAlarm,
        int snoozeMinutes,
        int maxSnooze
    ) {
        AlarmManager alarmManager = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        if (alarmManager == null) return;

        Intent intent = new Intent(context, ReminderReceiver.class);
        intent.putExtra(ReminderReceiver.EXTRA_ID, id);
        intent.putExtra(ReminderReceiver.EXTRA_TITLE, title);
        intent.putExtra(ReminderReceiver.EXTRA_BODY, body);
        intent.putExtra(ReminderReceiver.EXTRA_IS_ALARM, isAlarm);
        intent.putExtra(ReminderReceiver.EXTRA_SNOOZE_MINUTES, snoozeMinutes);
        intent.putExtra(ReminderReceiver.EXTRA_MAX_SNOOZE, maxSnooze);
        intent.putExtra(ReminderReceiver.EXTRA_SNOOZE_COUNT, 0);

        PendingIntent pending = PendingIntent.getBroadcast(
            context,
            id,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        if (isAlarm && Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            AlarmManager.AlarmClockInfo info = new AlarmManager.AlarmClockInfo(triggerAtMs, pending);
            alarmManager.setAlarmClock(info, pending);
        } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            alarmManager.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAtMs, pending);
        } else {
            alarmManager.setExact(AlarmManager.RTC_WAKEUP, triggerAtMs, pending);
        }

        persistEntry(context, id, title, body, triggerAtMs, isAlarm, snoozeMinutes, maxSnooze);
    }

    public static void cancel(Context context, int id) {
        AlarmManager alarmManager = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        if (alarmManager == null) return;

        Intent intent = new Intent(context, ReminderReceiver.class);
        PendingIntent pending = PendingIntent.getBroadcast(
            context,
            id,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        alarmManager.cancel(pending);
        removeEntry(context, id);
    }

    public static void rescheduleAll(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        String raw = prefs.getString(KEY_ALARMS, "[]");
        try {
            JSONArray arr = new JSONArray(raw);
            long now = System.currentTimeMillis();
            for (int i = 0; i < arr.length(); i++) {
                JSONObject o = arr.getJSONObject(i);
                long trigger = o.optLong("triggerAtMs", 0);
                if (trigger <= now) continue;
                schedule(
                    context,
                    o.getInt("id"),
                    o.optString("title", "Nexus"),
                    o.optString("body", ""),
                    trigger,
                    o.optBoolean("isAlarm", true),
                    o.optInt("snoozeMinutes", 5),
                    o.optInt("maxSnooze", 3)
                );
            }
        } catch (Exception ignored) {
        }
    }

    private static void persistEntry(
        Context context,
        int id,
        String title,
        String body,
        long triggerAtMs,
        boolean isAlarm,
        int snoozeMinutes,
        int maxSnooze
    ) {
        try {
            SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
            JSONArray arr = new JSONArray(prefs.getString(KEY_ALARMS, "[]"));
            JSONArray next = new JSONArray();
            for (int i = 0; i < arr.length(); i++) {
                JSONObject o = arr.getJSONObject(i);
                if (o.getInt("id") != id) next.put(o);
            }
            JSONObject entry = new JSONObject();
            entry.put("id", id);
            entry.put("title", title);
            entry.put("body", body);
            entry.put("triggerAtMs", triggerAtMs);
            entry.put("isAlarm", isAlarm);
            entry.put("snoozeMinutes", snoozeMinutes);
            entry.put("maxSnooze", maxSnooze);
            next.put(entry);
            prefs.edit().putString(KEY_ALARMS, next.toString()).apply();
        } catch (Exception ignored) {
        }
    }

    private static void removeEntry(Context context, int id) {
        try {
            SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
            JSONArray arr = new JSONArray(prefs.getString(KEY_ALARMS, "[]"));
            JSONArray next = new JSONArray();
            for (int i = 0; i < arr.length(); i++) {
                JSONObject o = arr.getJSONObject(i);
                if (o.getInt("id") != id) next.put(o);
            }
            prefs.edit().putString(KEY_ALARMS, next.toString()).apply();
        } catch (Exception ignored) {
        }
    }
}
