export function softwareRendering(renderer) {
  const gl = renderer.getContext();
  const info = gl.getExtension('WEBGL_debug_renderer_info');
  return Boolean(info && /swiftshader|llvmpipe|softpipe|software rasterizer|basic render driver/i
    .test(gl.getParameter(info.UNMASKED_RENDERER_WEBGL)));
}

export function cardPixelRatio(width, height, deviceRatio, software) {
  const cap = software ? Math.sqrt(860_000 / (width * height)) : 2;
  return Math.min(deviceRatio, 2, cap);
}
