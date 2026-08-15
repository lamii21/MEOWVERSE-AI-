import numpy as np
from PIL import Image


def render_heatmap_and_overlay(
    original_image: Image.Image, heatmap: np.ndarray, *, max_overlay_alpha: float = 0.6
) -> tuple[Image.Image, Image.Image]:
    """Turns a raw `(H, W)` Grad-CAM activation map (float32, `[0, 1]`,
    already resized to `original_image`'s dimensions) into two real
    images:

    - **Heatmap**: the activation map colorized with OpenCV's `JET`
      colormap — the same color scale used in the original Grad-CAM
      paper's own figures and every reference implementation (not an
      invented scale): blue = low importance, red = high importance.
    - **Overlay**: the heatmap alpha-blended onto the original photo,
      with **per-pixel alpha proportional to that pixel's importance**
      (`alpha = heatmap_value * max_overlay_alpha`) rather than one
      flat alpha over the whole image — low-importance regions stay
      close to the original photo, and even the single hottest pixel
      is capped at `max_overlay_alpha` (default 0.6) so the original
      image is never fully hidden under the heatmap (Phase 12 spec
      §10: "the original image must remain recognizable").

    Both returned images are real, finite-valued RGB PIL images sized
    to exactly match `original_image` — never a placeholder, never
    fabricated pixel data.
    """
    import cv2

    heatmap_uint8 = np.clip(heatmap * 255, 0, 255).astype(np.uint8)
    colored_bgr = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
    colored_rgb = cv2.cvtColor(colored_bgr, cv2.COLOR_BGR2RGB)
    heatmap_image = Image.fromarray(colored_rgb)

    original_rgb = np.array(original_image.convert("RGB")).astype(np.float32)
    colored_rgb_f = colored_rgb.astype(np.float32)
    alpha = (heatmap * max_overlay_alpha).astype(np.float32)[..., None]
    blended = original_rgb * (1 - alpha) + colored_rgb_f * alpha
    overlay_image = Image.fromarray(np.clip(blended, 0, 255).astype(np.uint8))

    return heatmap_image, overlay_image
