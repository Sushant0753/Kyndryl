import { useState, useRef, useEffect } from "react";
import { ChatMessage } from "@/types/chat";
import { useChatService } from "@/services/useChatService";

function parseBackendResponse(rawResponse: string): string {
  try {
    const data = JSON.parse(rawResponse);
    const responseText = data.response || data.answer || data.content || JSON.stringify(data);
    
    return responseText.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  } catch {
    return rawResponse;
  }
}

export function useChatMessage(initialMessages: ChatMessage[] = []) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [activeDocumentId, setActiveDocumentId] = useState<string | null>(null);
  const { sendMessage, uploadFile } = useChatService();
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages]);

  const addMessage = (msg: ChatMessage) =>
    setMessages((prev) => [...prev, msg]);

  const sendUserMessage = async (
    text: string, 
    file: File | null, 
    filenameOverride?: string,
    explicitDocId?: string
  ) => {
    
    const displayFilename = file ? file.name : filenameOverride;

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      text,
      isUser: true,
      timeStamp: Date.now(),
      ...(displayFilename ? { filename: displayFilename } : {}),
    };
    addMessage(userMsg);

    const botMsgId = crypto.randomUUID();
    addMessage({
      id: botMsgId,
      text: "Thinking...",
      isUser: false,
      timeStamp: Date.now(),
    });

    try {
      let docIdToUse = explicitDocId || activeDocumentId;

      if (file) {
        const uploadRes = await uploadFile(file);
        docIdToUse = uploadRes.document_id;
        setActiveDocumentId(docIdToUse); 
      } else if (explicitDocId) {
        setActiveDocumentId(explicitDocId); 
      }

      const finalDocId = docIdToUse || null;

      const rawResponse = await sendMessage(text, finalDocId);
      const botResponseText = parseBackendResponse(rawResponse);

      setMessages((prev) =>
        prev.map((m) =>
          m.id === botMsgId ? { ...m, text: botResponseText } : m
        )
      );
    } catch (err) {
      console.error("Chat Error:", err);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === botMsgId
            ? { ...m, text: "Error: Something went wrong. Please try again." }
            : m
        )
      );
    }
  };

  const regenerateMessage = (msg: ChatMessage) => {
    if (!msg.isUser) {
      const idx = messages.findIndex((m) => m.id === msg.id);
      if (idx > 0) {
        const lastUserMsg = messages[idx - 1];
        if (lastUserMsg.isUser) {
          sendUserMessage(lastUserMsg.text, null);
        }
      }
    }
  };

  const setDocumentId = (id: string) => setActiveDocumentId(id);

  return { 
    messages, 
    sendUserMessage, 
    containerRef, 
    regenerateMessage,
    setDocumentId 
  };
}