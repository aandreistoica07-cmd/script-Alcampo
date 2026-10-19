package com.alcampo.scraper;

import android.annotation.SuppressLint;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.os.Vibrator;
import android.view.KeyEvent;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;

import com.google.android.material.floatingactionbutton.ExtendedFloatingActionButton;

public class MainActivity extends AppCompatActivity {

    private static final String APP_URL = "https://alcampo.vercel.app/";
    private static final String PREFS_NAME = "alcampo_prefs";
    private static final String KEY_GITHUB_PAT = "github_pat";
    private static final String DEFAULT_GITHUB_PAT = "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";

    private WebView webView;
    private SwipeRefreshLayout swipeRefresh;
    private ExtendedFloatingActionButton fabGitHub;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        prefs.edit().putString(KEY_GITHUB_PAT, DEFAULT_GITHUB_PAT).apply();

        swipeRefresh = findViewById(R.id.swipeRefreshLayout);
        webView = findViewById(R.id.webView);
        fabGitHub = findViewById(R.id.fabGitHub);

        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);
        webSettings.setDatabaseEnabled(true);
        webSettings.setAllowFileAccess(true);
        webSettings.setLoadWithOverviewMode(true);
        webSettings.setUseWideViewPort(true);
        webSettings.setCacheMode(WebSettings.LOAD_DEFAULT);
        webSettings.setUserAgentString(webSettings.getUserAgentString() + " AlcampoAndroidApp/1.0");

        // JavaScript Interface for native features
        webView.addJavascriptInterface(new WebAppInterface(this), "AndroidBridge");

        webView.setWebChromeClient(new WebChromeClient());
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                if (request != null && request.getUrl() != null) {
                    String url = request.getUrl().toString();
                    if (url.startsWith("https://github.com") || url.startsWith("https://settings/tokens") || url.contains("github.com/settings/tokens")) {
                        try {
                            android.content.Intent intent = new android.content.Intent(android.content.Intent.ACTION_VIEW, request.getUrl());
                            startActivity(intent);
                            return true;
                        } catch (Exception e) {
                            e.printStackTrace();
                        }
                    }
                }
                return false;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                swipeRefresh.setRefreshing(false);
                view.evaluateJavascript(
                    "localStorage.setItem('alcampo_github_pat', '" + DEFAULT_GITHUB_PAT + "');",
                    null
                );
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                super.onReceivedError(view, request, error);
                // Fallback to local asset if network is down
                if (request.isForMainFrame()) {
                    webView.loadUrl("file:///android_asset/index.html");
                }
            }
        });

        swipeRefresh.setOnRefreshListener(() -> {
            webView.clearCache(true);
            webView.reload();
        });

        // Quick Launch GitHub Action Trigger
        fabGitHub.setOnClickListener(v -> {
            // Trigger GitHub Modal directly inside the WebView
            webView.loadUrl("javascript:if(typeof openGitHubModal === 'function'){ openGitHubModal(); }");
        });

        // Ensure fresh load of updated assets
        webView.clearCache(true);
        webView.loadUrl(APP_URL);
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK) {
            webView.evaluateJavascript(
                "(function() { " +
                "  var fs = document.getElementById('fullscreen-qr-overlay'); " +
                "  if (fs && fs.classList.contains('active')) { if (typeof closeFullscreenQr === 'function') closeFullscreenQr(); return true; } " +
                "  var qm = document.getElementById('qr-modal'); " +
                "  if (qm && qm.classList.contains('active')) { if (typeof closeQrModal === 'function') closeQrModal(); return true; } " +
                "  var gm = document.getElementById('github-modal'); " +
                "  if (gm && gm.classList.contains('active')) { if (typeof closeGitHubModal === 'function') closeGitHubModal(); return true; } " +
                "  return false; " +
                "})()",
                value -> {
                    if (!"true".equals(value)) {
                        runOnUiThread(() -> {
                            if (webView.canGoBack()) {
                                webView.goBack();
                            } else {
                                finish();
                            }
                        });
                    }
                }
            );
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    public class WebAppInterface {
        private final Context context;

        WebAppInterface(Context context) {
            this.context = context;
        }

        @JavascriptInterface
        public void setFullscreen(boolean enable) {
            runOnUiThread(() -> {
                try {
                    android.view.WindowManager.LayoutParams lp = getWindow().getAttributes();
                    if (enable) {
                        lp.screenBrightness = android.view.WindowManager.LayoutParams.BRIGHTNESS_OVERRIDE_FULL;
                        getWindow().setAttributes(lp);

                        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.R) {
                            getWindow().setDecorFitsSystemWindows(false);
                            android.view.WindowInsetsController controller = getWindow().getInsetsController();
                            if (controller != null) {
                                controller.hide(android.view.WindowInsets.Type.statusBars() | android.view.WindowInsets.Type.navigationBars());
                                controller.setSystemBarsBehavior(android.view.WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
                            }
                        } else {
                            getWindow().getDecorView().setSystemUiVisibility(
                                    android.view.View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                                            | android.view.View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                                            | android.view.View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                                            | android.view.View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                                            | android.view.View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                                            | android.view.View.SYSTEM_UI_FLAG_FULLSCREEN
                            );
                        }

                        // Seamless pure white edge-to-edge so no dark border can ever show at the bottom
                        getWindow().getDecorView().setBackgroundColor(android.graphics.Color.WHITE);
                        if (fabGitHub != null) fabGitHub.setVisibility(android.view.View.GONE);
                        if (swipeRefresh != null) {
                            swipeRefresh.setEnabled(false);
                            swipeRefresh.setBackgroundColor(android.graphics.Color.WHITE);
                        }
                        if (webView != null) webView.setBackgroundColor(android.graphics.Color.WHITE);

                        android.os.Vibrator v = (android.os.Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
                        if (v != null) v.vibrate(40);
                    } else {
                        lp.screenBrightness = android.view.WindowManager.LayoutParams.BRIGHTNESS_OVERRIDE_NONE;
                        getWindow().setAttributes(lp);

                        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.R) {
                            getWindow().setDecorFitsSystemWindows(true);
                            android.view.WindowInsetsController controller = getWindow().getInsetsController();
                            if (controller != null) {
                                controller.show(android.view.WindowInsets.Type.statusBars() | android.view.WindowInsets.Type.navigationBars());
                            }
                        } else {
                            getWindow().getDecorView().setSystemUiVisibility(android.view.View.SYSTEM_UI_FLAG_VISIBLE);
                        }

                        getWindow().getDecorView().setBackgroundColor(android.graphics.Color.parseColor("#060913"));
                        if (fabGitHub != null) fabGitHub.setVisibility(android.view.View.VISIBLE);
                        if (swipeRefresh != null) {
                            swipeRefresh.setEnabled(true);
                            swipeRefresh.setBackgroundColor(android.graphics.Color.TRANSPARENT);
                        }
                        if (webView != null) webView.setBackgroundColor(android.graphics.Color.TRANSPARENT);
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            });
        }

        @JavascriptInterface
        public void openExternalUrl(String url) {
            runOnUiThread(() -> {
                try {
                    android.content.Intent intent = new android.content.Intent(android.content.Intent.ACTION_VIEW, android.net.Uri.parse(url));
                    intent.addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK);
                    context.startActivity(intent);
                } catch (Exception e) {
                    e.printStackTrace();
                }
            });
        }

        @JavascriptInterface
        public void requestFullscreen(String cardNumber, String email, String balance) {
            setFullscreen(true);
        }

        @JavascriptInterface
        public void exitFullscreen() {
            setFullscreen(false);
        }

        @JavascriptInterface
        public void onWorkflowDispatched(String workflow) {
            runOnUiThread(() -> {
                Toast.makeText(context, "🚀 Iniciando workflow en GitHub Actions: " + workflow, Toast.LENGTH_LONG).show();
            });
        }

        @JavascriptInterface
        public void showToast(String message) {
            runOnUiThread(() -> Toast.makeText(context, message, Toast.LENGTH_SHORT).show());
        }
    }
}
