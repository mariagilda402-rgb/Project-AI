package com.nexus.mobile;

import android.app.KeyguardManager;
import android.content.Context;
import android.content.Intent;
import android.media.AudioAttributes;
import android.media.AudioManager;
import android.media.MediaPlayer;
import android.media.RingtoneManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.TextView;

import android.app.Activity;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public class AlarmRingActivity extends Activity {

    private MediaPlayer mediaPlayer;
    private Vibrator vibrator;
    private int alarmId;
    private String title;
    private String body;
    private int snoozeMinutes;
    private int maxSnooze;
    private int snoozeCount;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        showOnLockScreen();
        setContentView(R.layout.activity_alarm_ring);

        alarmId = getIntent().getIntExtra(ReminderReceiver.EXTRA_ID, 0);
        title = getIntent().getStringExtra(ReminderReceiver.EXTRA_TITLE);
        body = getIntent().getStringExtra(ReminderReceiver.EXTRA_BODY);
        snoozeMinutes = getIntent().getIntExtra(ReminderReceiver.EXTRA_SNOOZE_MINUTES, 5);
        maxSnooze = getIntent().getIntExtra(ReminderReceiver.EXTRA_MAX_SNOOZE, 3);
        snoozeCount = getIntent().getIntExtra(ReminderReceiver.EXTRA_SNOOZE_COUNT, 0);

        if (title == null) title = "Alarme";
        if (body == null) body = "";

        TextView timeView = findViewById(R.id.alarm_ring_time);
        TextView titleView = findViewById(R.id.alarm_ring_title);
        TextView bodyView = findViewById(R.id.alarm_ring_body);
        Button snoozeBtn = findViewById(R.id.alarm_snooze_btn);
        Button dismissBtn = findViewById(R.id.alarm_dismiss_btn);

        timeView.setText(new SimpleDateFormat("HH:mm", Locale.getDefault()).format(new Date()));
        titleView.setText(title);
        bodyView.setText(body.isEmpty() ? "Hora de acordar!" : body);

        if (snoozeCount >= maxSnooze) {
            snoozeBtn.setEnabled(false);
            snoozeBtn.setAlpha(0.4f);
        }

        snoozeBtn.setText("Soneca (" + snoozeMinutes + " min)");
        snoozeBtn.setOnClickListener(v -> snooze());
        dismissBtn.setOnClickListener(v -> dismiss());

        startAlarmFeedback();
    }

    private void showOnLockScreen() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true);
            setTurnScreenOn(true);
            KeyguardManager km = (KeyguardManager) getSystemService(Context.KEYGUARD_SERVICE);
            if (km != null) km.requestDismissKeyguard(this, null);
        } else {
            getWindow().addFlags(
                WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED
                    | WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON
                    | WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
            );
        }
    }

    private void startAlarmFeedback() {
        try {
            Uri alarmUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM);
            if (alarmUri == null) {
                alarmUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION);
            }
            mediaPlayer = new MediaPlayer();
            mediaPlayer.setDataSource(this, alarmUri);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                mediaPlayer.setAudioAttributes(new AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_ALARM)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                    .build());
            } else {
                mediaPlayer.setAudioStreamType(AudioManager.STREAM_ALARM);
            }
            mediaPlayer.setLooping(true);
            mediaPlayer.prepare();
            mediaPlayer.start();
        } catch (Exception ignored) {
        }

        vibrator = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
        if (vibrator != null && vibrator.hasVibrator()) {
            long[] pattern = {0, 800, 400, 800, 400, 800};
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vibrator.vibrate(VibrationEffect.createWaveform(pattern, 0));
            } else {
                vibrator.vibrate(pattern, 0);
            }
        }
    }

    private void stopAlarmFeedback() {
        if (mediaPlayer != null) {
            try {
                if (mediaPlayer.isPlaying()) mediaPlayer.stop();
                mediaPlayer.release();
            } catch (Exception ignored) {
            }
            mediaPlayer = null;
        }
        if (vibrator != null) vibrator.cancel();
    }

    private void dismiss() {
        stopAlarmFeedback();
        AlarmScheduler.cancel(this, alarmId);
        finish();
    }

    private void snooze() {
        if (snoozeCount >= maxSnooze) return;
        stopAlarmFeedback();
        long next = System.currentTimeMillis() + (long) snoozeMinutes * 60_000L;
        AlarmScheduler.schedule(this, alarmId, title, body + " (soneca)", next, true, snoozeMinutes, maxSnooze);
        finish();
    }

    @Override
    protected void onDestroy() {
        stopAlarmFeedback();
        super.onDestroy();
    }
}
