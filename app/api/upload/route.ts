import { NextRequest, NextResponse } from "next/server";
import { uploadedFiles } from "@/lib/fileStorage";

const ALLOWED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "text/plain",
  "image/png",
  "image/jpeg",
];

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get("file") as File;

    if (!file) {
      return NextResponse.json(
        { error: "No file provided" },
        { status: 400 }
      );
    }

    // Validate file type
    if (!ALLOWED_TYPES.includes(file.type)) {
      return NextResponse.json(
        { error: `File type "${file.type}" not allowed. Allowed types: ${ALLOWED_TYPES.join(", ")}` },
        { status: 400 }
      );
    }

    // Validate file size
    if (file.size > MAX_FILE_SIZE) {
      return NextResponse.json(
        { error: "File size exceeds the maximum limit of 10MB" },
        { status: 400 }
      );
    }

    // Generate unique ID
    const id = crypto.randomUUID();
    const uploaded_at = new Date().toISOString();

    // Convert file to buffer for storage
    const arrayBuffer = await file.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    // Store file metadata and data
    uploadedFiles.set(id, {
      filename: file.name,
      size: file.size,
      uploaded_at,
      data: buffer,
    });

    // Return success response
    return NextResponse.json({
      id,
      filename: file.name,
      size: file.size,
      uploaded_at,
    });
  } catch (error) {
    console.error("Upload error:", error);
    return NextResponse.json(
      { error: "Internal server error during upload" },
      { status: 500 }
    );
  }
}
