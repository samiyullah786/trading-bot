package com.aureon.mobile;

import android.content.Context;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/** Small, deterministic, offline execution core. No hosted intelligence, SDK or API is used. */
public final class LocalEngine {
    public static final class Step {
        public final String id, title, action;
        Step(String id, String title, String action) { this.id = id; this.title = title; this.action = action; }
    }
    public static final class Result {
        public final boolean success;
        public final String observation;
        Result(boolean success, String observation) { this.success = success; this.observation = observation; }
    }

    private final File workspace;
    public LocalEngine(Context context) {
        workspace = new File(context.getFilesDir(), "aureon_workspace");
        if (!workspace.exists() && !workspace.mkdirs()) throw new IllegalStateException("workspace unavailable");
    }

    public File workspace() { return workspace; }

    public List<Step> plan(String objective) {
        String text = objective == null ? "" : objective.toLowerCase(Locale.ROOT);
        List<Step> steps = new ArrayList<>();
        int n = 1;
        if (contains(text, "inspect", "workspace", "repository", "repo", "files"))
            steps.add(new Step("s" + n++, "Inspect workspace", "list"));
        if (contains(text, "create", "write", "generate", "file"))
            steps.add(new Step("s" + n++, "Prepare a workspace file", "create"));
        if (contains(text, "read", "open", "show"))
            steps.add(new Step("s" + n++, "Read the workspace manifest", "read"));
        if (contains(text, "verify", "check", "test"))
            steps.add(new Step("s" + n++, "Verify completed work", "verify"));
        if (steps.isEmpty()) steps.add(new Step("s1", "Clarify executable intent", "clarify"));
        return steps;
    }

    public Result execute(Step step) {
        try {
            switch (step.action) {
                case "list": return listFiles();
                case "create": return createMissionFile();
                case "read": return readManifest();
                case "verify": return verify();
                default: return new Result(false, "No safe local action can be derived from this objective.");
            }
        } catch (Exception e) {
            return new Result(false, "Execution error: " + e.getClass().getSimpleName());
        }
    }

    private Result listFiles() {
        File[] files = workspace.listFiles();
        if (files == null) return new Result(false, "Workspace cannot be enumerated.");
        StringBuilder out = new StringBuilder("Workspace files:");
        for (File f : files) out.append('\n').append(f.getName());
        return new Result(true, out.toString());
    }

    private Result createMissionFile() throws Exception {
        File file = safe("MISSION.md");
        String text = "# AUREON Mobile Mission\n\nThis file was created by the offline execution core.\n";
        try (FileOutputStream out = new FileOutputStream(file, false)) {
            out.write(text.getBytes(StandardCharsets.UTF_8));
        }
        return new Result(true, "Created " + file.getName() + " (" + file.length() + " bytes)");
    }

    private Result readManifest() throws Exception {
        File file = safe("MISSION.md");
        if (!file.isFile()) return new Result(false, "MISSION.md does not exist.");
        byte[] data = new byte[(int)Math.min(file.length(), 32768)];
        try (FileInputStream in = new FileInputStream(file)) { in.read(data); }
        return new Result(true, new String(data, StandardCharsets.UTF_8));
    }

    private Result verify() throws Exception {
        File file = safe("MISSION.md");
        if (!file.isFile()) return new Result(false, "Verification failed: expected artifact is missing.");
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] data = new byte[(int)Math.min(file.length(), 32768)];
        try (FileInputStream in = new FileInputStream(file)) { int read = in.read(data); digest.update(data, 0, Math.max(read, 0)); }
        return new Result(true, "Verification passed; SHA-256=" + hex(digest.digest()));
    }

    private File safe(String name) throws Exception {
        File target = new File(workspace, name);
        String root = workspace.getCanonicalPath() + File.separator;
        if (!target.getCanonicalPath().startsWith(root)) throw new SecurityException("path escape");
        return target;
    }

    private static boolean contains(String text, String... words) {
        for (String word : words) if (text.contains(word)) return true;
        return false;
    }

    private static String hex(byte[] data) {
        StringBuilder out = new StringBuilder(data.length * 2);
        for (byte b : data) out.append(String.format(Locale.ROOT, "%02x", b & 255));
        return out.toString();
    }
}
