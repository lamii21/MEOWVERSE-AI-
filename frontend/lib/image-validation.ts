export const ACCEPTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];
export const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024;
export const MIN_DIMENSION_PX = 64;

export interface ValidationResult {
  valid: boolean;
  error?: string;
}

function readImageDimensions(file: File): Promise<{ width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      resolve({ width: img.naturalWidth, height: img.naturalHeight });
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("unreadable"));
    };
    img.src = url;
  });
}

export async function validateImageFile(file: File): Promise<ValidationResult> {
  if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) {
    return { valid: false, error: "MeowVerse needs a valid image (JPEG, PNG, or WebP)." };
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return { valid: false, error: "That photo is a bit too big — try one under 10MB." };
  }

  try {
    const { width, height } = await readImageDimensions(file);
    if (width < MIN_DIMENSION_PX || height < MIN_DIMENSION_PX) {
      return { valid: false, error: "That image is too small to see the whiskers. Try a larger one." };
    }
  } catch {
    return { valid: false, error: "MeowVerse couldn't read that file. Try a different photo." };
  }

  return { valid: true };
}
