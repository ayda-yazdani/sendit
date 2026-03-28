const CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"; // Excludes 0/O, 1/I/L

export function generateJoinCode(length: number = 6): string {
  let code = "";
  for (let i = 0; i < length; i++) {
    code += CHARS.charAt(Math.floor(Math.random() * CHARS.length));
  }
  return code;
}
