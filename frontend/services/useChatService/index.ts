import { VoiceChatResponse } from "@/types/chat";

export function useChatService() {
  const uploadFile = async (file: File) => {
    const fd = new FormData();
    fd.append("file", file);

    const res = await fetch("/api/upload", {
      method: "POST",
      body: fd,
    });

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(errorText || "Upload failed");
    }
    
    return await res.json();
  };

  const sendMessage = async (message: string, documentId: string | null) => {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: message,
        document_id: documentId,
      }),
    });

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(errorText || "Chat failed");
    }

    return await res.text();
  };

  const sendVoiceChat = async (audioBlob: Blob): Promise<VoiceChatResponse> => {
    const fd = new FormData();
    fd.append("file", audioBlob);

    const res = await fetch("/api/voice-chat", {
      method: "POST",
      body: fd,
    });

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(errorText || "Voice chat failed");
    }

    return await res.json();
  };

  return { sendMessage, uploadFile, sendVoiceChat };
}