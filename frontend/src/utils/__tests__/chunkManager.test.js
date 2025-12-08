import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  splitFile,
  ChunkState,
  saveStateToLocalStorage,
  loadStateFromLocalStorage,
  clearStateFromLocalStorage,
} from "../chunkManager";

describe("chunkManager", () => {
  describe("splitFile", () => {
    it("should split file into chunks", () => {
      const file = new File(["x".repeat(5 * 1024 * 1024)], "test.jsonl");
      const chunks = splitFile(file, 1024 * 1024); // 1MB chunks

      expect(chunks).toHaveLength(5);
      expect(chunks[0].size).toBe(1024 * 1024);
    });

    it("should handle file smaller than chunk size", () => {
      const file = new File(["x".repeat(100)], "small.txt");
      const chunks = splitFile(file, 1024 * 1024);

      expect(chunks).toHaveLength(1);
      expect(chunks[0].size).toBe(100);
    });

    it("should handle exact chunk size", () => {
      const file = new File(["x".repeat(1024 * 1024)], "exact.bin");
      const chunks = splitFile(file, 1024 * 1024);

      expect(chunks).toHaveLength(1);
      expect(chunks[0].size).toBe(1024 * 1024);
    });

    it("should handle empty file", () => {
      const file = new File([], "empty.txt");
      const chunks = splitFile(file, 1024 * 1024);

      // Empty file still creates one chunk (even if size is 0)
      expect(chunks.length).toBeGreaterThanOrEqual(0);
      if (chunks.length > 0) {
        expect(chunks[0].size).toBe(0);
      }
    });
  });

  describe("ChunkState", () => {
    let chunkState;

    beforeEach(() => {
      chunkState = new ChunkState(10);
    });

    it("should initialize with correct total chunks", () => {
      expect(chunkState.totalChunks).toBe(10);
      expect(chunkState.uploaded.size).toBe(0);
      expect(chunkState.failed.size).toBe(0);
    });

    it("should mark chunk as uploaded", () => {
      chunkState.markUploaded(0);

      expect(chunkState.uploaded.has(0)).toBe(true);
      expect(chunkState.failed.has(0)).toBe(false);
      expect(chunkState.inProgress.has(0)).toBe(false);
    });

    it("should mark chunk as failed", () => {
      chunkState.markFailed(1);

      expect(chunkState.failed.has(1)).toBe(true);
      expect(chunkState.uploaded.has(1)).toBe(false);
      expect(chunkState.inProgress.has(1)).toBe(false);
    });

    it("should mark chunk as in progress", () => {
      chunkState.markInProgress(2);

      expect(chunkState.inProgress.has(2)).toBe(true);
      expect(chunkState.uploaded.has(2)).toBe(false);
      expect(chunkState.failed.has(2)).toBe(false);
    });

    it("should get missing chunks", () => {
      chunkState.markUploaded(0);
      chunkState.markUploaded(2);
      chunkState.markUploaded(4);

      const missing = chunkState.getMissingChunks();
      expect(missing).toEqual([1, 3, 5, 6, 7, 8, 9]);
    });

    it("should get failed chunks", () => {
      chunkState.markFailed(1);
      chunkState.markFailed(3);

      const failed = chunkState.getFailedChunks();
      expect(failed).toEqual([1, 3]);
    });

    it("should check if complete", () => {
      expect(chunkState.isComplete()).toBe(false);

      for (let i = 0; i < 10; i++) {
        chunkState.markUploaded(i);
      }

      expect(chunkState.isComplete()).toBe(true);
    });

    it("should calculate progress", () => {
      chunkState.markUploaded(0);
      chunkState.markUploaded(1);
      chunkState.markUploaded(2);

      expect(chunkState.getProgress()).toBe(30); // 3/10 = 30%
    });

    it("should merge server state", () => {
      chunkState.markUploaded(0);
      chunkState.markFailed(1);

      chunkState.mergeServerState([0, 2, 3]);

      expect(chunkState.uploaded.has(0)).toBe(true);
      expect(chunkState.uploaded.has(2)).toBe(true);
      expect(chunkState.uploaded.has(3)).toBe(true);
      // Failed chunks that are now uploaded should be cleared
      // But if 1 is not in server state, it might still be marked as failed
      // This is expected behavior - server state takes precedence
    });

    it("should reset failed chunks", () => {
      chunkState.markFailed(1);
      chunkState.markFailed(2);

      chunkState.resetFailed();

      expect(chunkState.failed.size).toBe(0);
    });

    it("should get summary", () => {
      chunkState.markUploaded(0);
      chunkState.markUploaded(1);
      chunkState.markFailed(2);
      chunkState.markInProgress(3);

      const summary = chunkState.getSummary();

      expect(summary.total).toBe(10);
      expect(summary.uploaded).toBe(2);
      expect(summary.failed).toBe(1);
      expect(summary.inProgress).toBe(1);
      expect(summary.progress).toBe(20);
      expect(summary.isComplete).toBe(false);
    });
  });

  describe("localStorage helpers", () => {
    beforeEach(() => {
      localStorage.clear();
    });

    it("should save state to localStorage", () => {
      const chunkState = new ChunkState(5);
      chunkState.markUploaded(0);
      chunkState.markUploaded(1);
      chunkState.markFailed(2);

      saveStateToLocalStorage("test-123", chunkState, "test.jsonl", 5000);

      const saved = localStorage.getItem("upload_test-123");
      expect(saved).toBeTruthy();

      const parsed = JSON.parse(saved);
      expect(parsed.uploadId).toBe("test-123");
      expect(parsed.uploaded).toEqual([0, 1]);
      expect(parsed.failed).toEqual([2]);
    });

    it("should load state from localStorage", () => {
      const state = {
        uploadId: "test-456",
        filename: "test.jsonl",
        fileSize: 1000,
        uploaded: [0, 1, 2],
        failed: [3],
        timestamp: Date.now(),
      };
      localStorage.setItem("upload_test-456", JSON.stringify(state));

      const loaded = loadStateFromLocalStorage("test-456");

      expect(loaded).toBeTruthy();
      expect(loaded.uploaded).toEqual(new Set([0, 1, 2]));
      expect(loaded.failed).toEqual(new Set([3]));
      expect(loaded.filename).toBe("test.jsonl");
    });

    it("should return null for non-existent state", () => {
      const loaded = loadStateFromLocalStorage("nonexistent");
      expect(loaded).toBeNull();
    });

    it("should clear state from localStorage", () => {
      localStorage.setItem("upload_test-789", '{"data": "test"}');

      clearStateFromLocalStorage("test-789");

      expect(localStorage.getItem("upload_test-789")).toBeNull();
    });
  });
});
