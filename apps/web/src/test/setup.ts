import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(cleanup);

vi.stubGlobal("ResizeObserver", class {
  observe() {}
  disconnect() {}
});

Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
  value: () => ({
    setTransform() {}, clearRect() {}, beginPath() {}, moveTo() {}, lineTo() {},
    stroke() {}, arc() {}, fill() {}, fillRect() {}, strokeRect() {}, closePath() {},
  }),
});
