// In-memory storage for uploaded files (for demonstration)
// In production, you'd use a database or file storage service
export const uploadedFiles = new Map<string, { 
  filename: string; 
  size: number; 
  uploaded_at: string; 
  data: Buffer;
}>();
