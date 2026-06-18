# Project-specific ProGuard/R8 rules.
#
# Keep JavaScript bridge methods that are invoked by the bundled WebView app.
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}

# Keep the native bridge classes available for WebView reflection.
-keep class com.nexus.mobile.MainActivity$NexusAndroidBridge { *; }
-keep class com.nexus.mobile.MainActivity$WebAppInterface { *; }
