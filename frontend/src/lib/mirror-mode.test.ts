import {
  buildDefaultMirrorMode,
  shouldEnableMirrorMode,
} from "./mirror-mode";

describe("mirror mode defaults", () => {
  test("enables packet mirror controls only for multi-image uploads", () => {
    expect(shouldEnableMirrorMode("image", 2)).toBe(true);
    expect(shouldEnableMirrorMode("image", 1)).toBe(false);
    expect(shouldEnableMirrorMode("video", 2)).toBe(false);
  });

  test("builds the ImageGen packet contract sent to the backend", () => {
    expect(buildDefaultMirrorMode("image", 3)).toEqual({
      enabled: true,
      packetMode: true,
      sidecarMode: true,
      assetRegistry: true,
      routeRegistry: true,
      backendContract: true,
      visualRepair: true,
      targetFidelity: "strict",
    });
  });
});
