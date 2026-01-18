"use client";

import ChatInput from "@/components/ChatInput";
import { useRouter } from "next/navigation";
import React, { useState } from "react";
import { useChatService } from "@/services/useChatService";

export default function Home() {
  const router = useRouter();
  const [isPreparing, setIsPreparing] = useState(false);
  const { uploadFile } = useChatService();

  const handleSend = async (text: string, file: File | null) => {
    if (!text.trim() && !file) return;
    setIsPreparing(true);

    const sessionId = crypto.randomUUID();
    let documentId: string | null = null;
    let filename: string | null = null;

    try {
      if (file) {
        if (file.type !== "application/pdf") {
          console.warn("Only PDF files are expected.");
        }
        
        filename = file.name;
        const uploadRes = await uploadFile(file);
        documentId = uploadRes.document_id;
      }

      window.sessionStorage.setItem(
        `first-message-${sessionId}`,
        JSON.stringify({
          text,
          documentId,
          filename,
        })
      );

      router.push(`/chat/${sessionId}/`);
      
    } catch (err) {
      console.error("Failed to initialize chat:", err);
      setIsPreparing(false);
    }
  };

  return (
    <div className="h-screen w-screen bg-dots text-white">
      <main className="ml-16 h-full">
        <div className="h-full flex flex-col items-center justify-center px-4">
          <h1 className="text-4xl font-bold text-blue-400 mb-10">
            How can I help you today?
          </h1>

          {isPreparing && (
            <p className="text-sm text-neutral-400 mb-4 animate-pulse">
              Setting up your workspace...
            </p>
          )}

          <ChatInput sendUserMessage={handleSend} />
        </div>
      </main>
    </div>
  );
}