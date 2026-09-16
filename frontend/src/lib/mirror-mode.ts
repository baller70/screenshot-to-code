import { MirrorModeConfig } from "../types";

type InputMode = "image" | "video" | "text";

export function shouldEnableMirrorMode(
  inputMode: InputMode,
  screenshotCount: number
): boolean {
  return inputMode === "image" && screenshotCount > 1;
}

export function buildDefaultMirrorMode(
  inputMode: InputMode,
  screenshotCount: number
): MirrorModeConfig {
  const enabled = shouldEnableMirrorMode(inputMode, screenshotCount);
  return {
    enabled,
    packetMode: enabled,
    sidecarMode: enabled,
    assetRegistry: enabled,
    routeRegistry: enabled,
    backendContract: enabled,
    visualRepair: enabled,
    targetFidelity: enabled ? "strict" : "standard",
  };
}
