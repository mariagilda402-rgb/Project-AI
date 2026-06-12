import re

with open('mobile-apk/app/src/main/AndroidManifest.xml', 'r', encoding='utf-8') as f:
    c = f.read()

permissions = '''
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_MICROPHONE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_MEDIA_PROJECTION" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
'''

service_tag = '''
        <service
            android:name=".JarvisCallService"
            android:foregroundServiceType="microphone|mediaProjection"
            android:exported="false" />
'''

if 'FOREGROUND_SERVICE_MICROPHONE' not in c:
    c = c.replace('<uses-permission android:name="android.permission.RECORD_AUDIO" />', '<uses-permission android:name="android.permission.RECORD_AUDIO" />\n' + permissions)
    
if 'JarvisCallService' not in c:
    c = c.replace('</application>', service_tag + '\n    </application>')
    
with open('mobile-apk/app/src/main/AndroidManifest.xml', 'w', encoding='utf-8') as f:
    f.write(c)
