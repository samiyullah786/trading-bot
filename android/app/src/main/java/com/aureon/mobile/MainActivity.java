package com.aureon.mobile;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;

/** Native Android control surface for AUREON's offline local engine. */
public final class MainActivity extends Activity {
    private static final int EXPORT_REQUEST = 42;
    private LocalEngine engine;
    private MissionStore store;
    private EditText objective;
    private TextView status;
    private String lastReport = "";

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        engine = new LocalEngine(this);
        store = new MissionStore(this);
        buildUi();
    }

    private void buildUi() {
        int pad = dp(18);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(pad, pad, pad, pad);

        TextView title = new TextView(this);
        title.setText("AUREON\nAutonomous Mobile Engine");
        title.setTextSize(25);
        title.setGravity(Gravity.CENTER_VERTICAL);
        root.addView(title, new LinearLayout.LayoutParams(-1, dp(90)));

        TextView mode = new TextView(this);
        mode.setText("OFFLINE CORE  •  NO HOSTED AI  •  SANDBOXED WORKSPACE");
        mode.setTextSize(12);
        root.addView(mode, new LinearLayout.LayoutParams(-1, dp(42)));

        objective = new EditText(this);
        objective.setHint("Describe the mission… e.g. inspect and verify the workspace");
        objective.setSingleLine(false);
        objective.setMinLines(3);
        root.addView(objective, new LinearLayout.LayoutParams(-1, dp(120)));

        LinearLayout buttons = new LinearLayout(this);
        buttons.setOrientation(LinearLayout.HORIZONTAL);
        Button run = new Button(this); run.setText("RUN MISSION");
        Button history = new Button(this); history.setText("HISTORY");
        Button export = new Button(this); export.setText("EXPORT");
        buttons.addView(run, new LinearLayout.LayoutParams(0, dp(52), 1));
        buttons.addView(history, new LinearLayout.LayoutParams(0, dp(52), 1));
        buttons.addView(export, new LinearLayout.LayoutParams(0, dp(52), 1));
        root.addView(buttons);

        status = new TextView(this);
        status.setTextSize(14);
        status.setTextIsSelectable(true);
        ScrollView scroll = new ScrollView(this);
        scroll.addView(status);
        root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));

        run.setOnClickListener(v -> runMission());
        history.setOnClickListener(v -> showHistory());
        export.setOnClickListener(v -> exportReport());
        setContentView(root);
    }

    private void runMission() {
        final String mission = objective.getText().toString().trim();
        if (mission.isEmpty()) { status.setText("Enter a mission first."); return; }
        status.setText("Planning locally…\nNo network or external AI is consulted.");
        new Thread(() -> {
            List<LocalEngine.Step> plan = engine.plan(mission);
            StringBuilder report = new StringBuilder();
            report.append("MISSION\n").append(mission).append("\n\nPLAN\n");
            boolean allPassed = true;
            for (int i = 0; i < plan.size(); i++) {
                LocalEngine.Step step = plan.get(i);
                report.append(i + 1).append(". ").append(step.title).append("\n");
                LocalEngine.Result result = engine.execute(step);
                report.append("   ").append(result.success ? "PASS" : "FAIL").append(" — ")
                        .append(result.observation).append("\n");
                if (!result.success) allPassed = false;
            }
            report.append("\nFINAL: ").append(allPassed ? "PROVEN LOCALLY" : "NOT PROVEN").append("\n");
            String finished = report.toString();
            lastReport = finished;
            try { store.append(finished); } catch (Exception ignored) { }
            runOnUiThread(() -> status.setText(finished));
        }).start();
    }

    private void showHistory() {
        new Thread(() -> {
            try {
                String history = store.read();
                runOnUiThread(() -> status.setText(history.isEmpty() ? "No mission history yet." : history));
            } catch (Exception e) {
                runOnUiThread(() -> status.setText("History unavailable."));
            }
        }).start();
    }

    private void exportReport() {
        if (lastReport.isEmpty()) { status.setText("Run a mission before exporting."); return; }
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        intent.setType("text/plain");
        intent.putExtra(Intent.EXTRA_TITLE, "aureon-mission-report.txt");
        startActivityForResult(intent, EXPORT_REQUEST);
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == EXPORT_REQUEST && resultCode == RESULT_OK && data != null) {
            Uri uri = data.getData();
            try (OutputStream out = getContentResolver().openOutputStream(uri)) {
                if (out == null) throw new IllegalStateException("output unavailable");
                out.write(lastReport.getBytes(StandardCharsets.UTF_8));
                status.append("\nReport exported successfully.");
            } catch (Exception e) {
                status.append("\nExport failed: " + e.getClass().getSimpleName());
            }
        }
    }

    private int dp(int value) { return (int)(value * getResources().getDisplayMetrics().density + 0.5f); }
}
