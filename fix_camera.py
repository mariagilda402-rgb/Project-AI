import re

with open('mobile-apk/app/src/main/java/com/nexus/mobile/MainActivity.java', 'r', encoding='utf-8') as f:
    c = f.read()

camera_imports = '''
import android.provider.MediaStore;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.util.Base64;
import java.io.ByteArrayOutputStream;
'''

if 'import android.provider.MediaStore;' not in c:
    c = c.replace('import android.os.Bundle;', 'import android.os.Bundle;\n' + camera_imports)

camera_fields = '''
    private static final int REQUEST_IMAGE_CAPTURE = 4403;
    private String currentPhotoPath = "";
'''

if 'REQUEST_IMAGE_CAPTURE' not in c:
    c = c.replace('private static final int PERMISSION_REQUEST_CODE = 4401;', 'private static final int PERMISSION_REQUEST_CODE = 4401;\n' + camera_fields)


camera_methods = '''
    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_IMAGE_CAPTURE && resultCode == RESULT_OK) {
            // Using the thumbnail for simplicity, full resolution would require FileProvider setup
            // which requires xml/file_paths.xml creation. If resolution is too low, we will change it.
            if (data != null && data.getExtras() != null) {
                Bitmap imageBitmap = (Bitmap) data.getExtras().get("data");
                if(imageBitmap != null) {
                    ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream();  
                    imageBitmap.compress(Bitmap.CompressFormat.JPEG, 100, byteArrayOutputStream);
                    byte[] byteArray = byteArrayOutputStream.toByteArray();
                    String encoded = Base64.encodeToString(byteArray, Base64.NO_WRAP);
                    
                    runOnUiThread(() -> {
                        webView.evaluateJavascript("javascript:if(window.receiveCameraImage) window.receiveCameraImage('" + encoded + "');", null);
                    });
                }
            }
        }
    }
'''

if 'onActivityResult' not in c:
    # Insert before the inner class WebAppInterface
    c = c.replace('private class WebAppInterface', camera_methods + '\n    private class WebAppInterface')

interface_method = '''
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
'''

if 'openNativeCamera' not in c:
    c = c.replace('public void stopJarvisCall() {', interface_method + '\n        public void stopJarvisCall() {')

with open('mobile-apk/app/src/main/java/com/nexus/mobile/MainActivity.java', 'w', encoding='utf-8') as f:
    f.write(c)
