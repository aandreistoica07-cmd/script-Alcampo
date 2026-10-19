package com.alcampo.scraper;

import android.annotation.SuppressLint;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.view.WindowManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.widget.Button;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

public class FullscreenQrActivity extends AppCompatActivity {

    public static final String EXTRA_CARD_NUMBER = "extra_card_number";
    public static final String EXTRA_EMAIL = "extra_email";
    public static final String EXTRA_BALANCE = "extra_balance";

    public static void start(Context context, String cardNumber, String email, String balance) {
        Intent intent = new Intent(context, FullscreenQrActivity.class);
        intent.putExtra(EXTRA_CARD_NUMBER, cardNumber);
        intent.putExtra(EXTRA_EMAIL, email);
        intent.putExtra(EXTRA_BALANCE, balance);
        context.startActivity(intent);
    }

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Force maximum display brightness for optical cash register scanner reading
        WindowManager.LayoutParams layoutParams = getWindow().getAttributes();
        layoutParams.screenBrightness = WindowManager.LayoutParams.BRIGHTNESS_OVERRIDE_FULL;
        getWindow().setAttributes(layoutParams);

        // Immersive sticky fullscreen
        hideSystemUI();

        setContentView(R.layout.activity_fullscreen_qr);

        String cardNumber = getIntent().getStringExtra(EXTRA_CARD_NUMBER);
        if (cardNumber == null || cardNumber.trim().isEmpty()) {
            cardNumber = "2801234567890";
        }
        String email = getIntent().getStringExtra(EXTRA_EMAIL);
        String balance = getIntent().getStringExtra(EXTRA_BALANCE);

        TextView tvTitle = findViewById(R.id.tvScannerTitle);
        if (balance != null && !balance.isEmpty()) {
            tvTitle.setText("⚡ CLUB ALCAMPO • SALDO: " + balance + " €");
        } else {
            tvTitle.setText("⚡ CLUB ALCAMPO • ESCÁNER DE CAJA");
        }

        WebView qrWebView = findViewById(R.id.qrWebView);
        WebSettings settings = qrWebView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);

        String cleanDigits = cardNumber.replaceAll("\\D+", "");
        if (cleanDigits.isEmpty()) cleanDigits = cardNumber;

        String formatted = formatCardNumber(cleanDigits);

        // Self-contained pure-contrast HTML scanner page with QRCode.js & JsBarcode
        String html = "<!DOCTYPE html><html><head><meta charset='utf-8'>" +
                "<meta name='viewport' content='width=device-width, initial-scale=1.0, user-scalable=no'>" +
                "<script src='https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js'></script>" +
                "<script src='https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js'></script>" +
                "<style>" +
                "* { box-sizing: border-box; margin: 0; padding: 0; }" +
                "body { background: #ffffff; color: #000000; font-family: monospace; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; padding: 12px; }" +
                "#qrcode { padding: 8px; background: #ffffff; }" +
                "#qrcode img, #qrcode canvas { max-width: 75vw !important; max-height: 42vh !important; width: auto !important; height: auto !important; }" +
                "#barcode-svg { max-width: 95vw; height: auto; max-height: 85px; margin-top: 10px; }" +
                ".card-num { font-size: 24px; font-weight: 900; letter-spacing: 2px; color: #000000; margin-top: 10px; text-align: center; }" +
                ".email-txt { font-size: 13px; color: #444444; margin-top: 4px; text-align: center; word-break: break-all; }" +
                "</style></head><body>" +
                "<div id='qrcode'></div>" +
                "<svg id='barcode-svg'></svg>" +
                "<div class='card-num'>" + formatted + "</div>" +
                "<div class='email-txt'>" + (email != null ? email : "") + "</div>" +
                "<script>" +
                "new QRCode(document.getElementById('qrcode'), { text: '" + cleanDigits + "', width: 340, height: 340, colorDark: '#000000', colorLight: '#ffffff', correctLevel: QRCode.CorrectLevel.H });" +
                "try { JsBarcode('#barcode-svg', '" + cleanDigits + "', { format: '" + (cleanDigits.length() == 13 ? "EAN13" : "CODE128") + "', width: 2.6, height: 80, displayValue: true, fontSize: 16, background: '#ffffff', lineColor: '#000000' }); } catch(e){}" +
                "</script></body></html>";

        qrWebView.loadDataWithBaseURL("https://alcampo.vercel.app", html, "text/html", "UTF-8", null);

        Button btnClose = findViewById(R.id.btnCloseFullscreen);
        btnClose.setOnClickListener(v -> finish());
    }

    private void hideSystemUI() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            WindowInsetsController controller = getWindow().getInsetsController();
            if (controller != null) {
                controller.hide(WindowInsets.Type.statusBars() | WindowInsets.Type.navigationBars());
                controller.setSystemBarsBehavior(WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
            }
        } else {
            getWindow().getDecorView().setSystemUiVisibility(
                    View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                            | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                            | View.SYSTEM_UI_FLAG_FULLSCREEN
            );
        }
    }

    private String formatCardNumber(String num) {
        if (num.length() == 13) {
            return num.substring(0, 1) + " " + num.substring(1, 7) + " " + num.substring(7, 13);
        }
        return num.replaceAll("(.{4})", "$1 ").trim();
    }
}
