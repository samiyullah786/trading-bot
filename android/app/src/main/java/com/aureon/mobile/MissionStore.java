package com.aureon.mobile;

import android.content.Context;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;

/** Append-only, bounded local mission history. */
public final class MissionStore {
    private static final int MAX_BYTES = 512 * 1024;
    private final File history;

    public MissionStore(Context context) {
        history = new File(context.getFilesDir(), "mission-history.log");
    }

    public synchronized void append(String report) throws Exception {
        byte[] incoming = (report + "\n\n--- MISSION END ---\n").getBytes(StandardCharsets.UTF_8);
        if (incoming.length > MAX_BYTES) throw new IllegalArgumentException("report too large");
        byte[] old = readBytes();
        int keep = Math.max(0, MAX_BYTES - incoming.length);
        int start = Math.max(0, old.length - keep);
        try (FileOutputStream out = new FileOutputStream(history, false)) {
            out.write(old, start, old.length - start);
            out.write(incoming);
        }
    }

    public synchronized String read() throws Exception {
        return new String(readBytes(), StandardCharsets.UTF_8);
    }

    private byte[] readBytes() throws Exception {
        if (!history.isFile()) return new byte[0];
        long length = Math.min(history.length(), MAX_BYTES);
        byte[] data = new byte[(int) length];
        try (FileInputStream in = new FileInputStream(history)) {
            int offset = 0;
            while (offset < data.length) {
                int count = in.read(data, offset, data.length - offset);
                if (count < 0) break;
                offset += count;
            }
            if (offset == data.length) return data;
            byte[] exact = new byte[offset];
            System.arraycopy(data, 0, exact, 0, offset);
            return exact;
        }
    }
}
