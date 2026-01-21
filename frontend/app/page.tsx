"use client";

import ChatInput from "@/components/ChatInput";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useChatService } from "@/services/useChatService";

export default function Home() {
  const router = useRouter();
  const [isPreparing, setIsPreparing] = useState(false);
  const { uploadFile, sendVoiceChat } = useChatService();

  const handleSend = async (text: string, file: File | null) => {
    if (!text.trim() && !file) return;
    setIsPreparing(true);

    const sessionId = crypto.randomUUID();
    let documentId: string | null = null;
    let filename: string | null = null;

    try {
      if (file) {
        const allowedTypes = [
          "application/pdf",
          "image/png",
          "image/jpeg",
          "image/jpg",
        ];

        if (!allowedTypes.includes(file.type)) {
          setIsPreparing(false);
          return;
        }
        filename = file.name;
        const uploadRes = await uploadFile(file);
        documentId = uploadRes.document_id;
      }
      window.sessionStorage.setItem(
        `first-message-${sessionId}`,
        JSON.stringify({
          type: "text_intent",
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

  const handleVoice = async (audioBlob: Blob) => {
    setIsPreparing(true);
    const sessionId = crypto.randomUUID();

    try {
      const data = await sendVoiceChat(audioBlob);
      window.sessionStorage.setItem(
        `first-message-${sessionId}`,
        JSON.stringify({
          type: "voice_result",
          userText: data.transcribed_text,
          botText: data.chat_response,
          audioUrl: data.audio_url
        })
      );
      router.push(`/chat/${sessionId}/`);

    } catch (err) {
      console.error("Failed to process voice on home:", err);
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

          <ChatInput 
            sendUserMessage={handleSend} 
            sendVoiceMessage={handleVoice} 
          />
        </div>
      </main>
    </div>
  );
}