import { useState, useRef, useEffect } from "react";
import { ChatMessage } from "@/types/chat";
import { useChatService } from "@/services/useChatService";

function generateId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `msg_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

function parseBackendResponse(rawResponse: string): string {
  try {
    const data = JSON.parse(rawResponse);
    const responseText = data.response || data.answer || data.content || JSON.stringify(data);
    return responseText.replace(/\*\*(.+?)\*\*/gs, "<strong>$1</strong>");
  } catch {
    return rawResponse;
  }
}

function speakWithBrowser(text: string, lang: string = 'en-IN') {
  if (typeof window === 'undefined' || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const plain = text.replace(/<[^>]+>/g, '').replace(/\*\*/g, '');
  const utterance = new SpeechSynthesisUtterance(plain);
  utterance.lang = lang;
  utterance.rate = 0.95;
  window.speechSynthesis.speak(utterance);
}

export function useChatMessage(initialMessages: ChatMessage[] = []) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [activeDocumentId, setActiveDocumentId] = useState<string | null>(null);
  const { sendMessage, uploadFile, sendVoiceChat, synthesizeSpeech } = useChatService();
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
    ttsEnabled?: boolean,
    filenameOverride?: string,
    explicitDocId?: string
  ) => {
    const displayFilename = file ? file.name : filenameOverride;

    const userMsg: ChatMessage = {
      id: generateId(),
      text,
      isUser: true,
      timeStamp: Date.now(),
      ...(displayFilename ? { filename: displayFilename } : {}),
    };
    addMessage(userMsg);

    const botMsgId = generateId();
    addMessage({
      id: botMsgId,
      text: "",
      isUser: false,
      timeStamp: Date.now(),
      isLoading: true,
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

      // If there's no query text, just confirm the file upload and stop — don't hit the chat endpoint
      if (!text.trim()) {
        const docName = file ? file.name : filenameOverride || "your document";
        setMessages((prev) =>
          prev.map((m) =>
            m.id === botMsgId
              ? { ...m, text: `Document "${docName}" is ready. Ask me anything about it!`, isLoading: false }
              : m
          )
        );
        return;
      }

      const finalDocId = docIdToUse || null;

      const rawResponse = await sendMessage(text, finalDocId);
      const botResponseText = parseBackendResponse(rawResponse);

      setMessages((prev) =>
        prev.map((m) =>
          m.id === botMsgId
            ? { ...m, text: botResponseText, isLoading: false }
            : m
        )
      );

      if (ttsEnabled && botResponseText) {
        try {
          const plainText = botResponseText.replace(/<[^>]+>/g, '');
          const ttsResult = await synthesizeSpeech(plainText);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === botMsgId
                ? { ...m, audioUrl: ttsResult.audio_url }
                : m
            )
          );
        } catch (ttsErr) {
          console.error("TTS synthesis failed, falling back to browser TTS:", ttsErr);
          speakWithBrowser(botResponseText);
        }
      }
    } catch (err) {
      console.error("Chat Error:", err);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === botMsgId
            ? {
                ...m,
                text: "Error: Something went wrong. Please try again.",
                isLoading: false
              }
            : m
        )
      );
    }
  };

  const sendVoiceMessage = async (audioBlob: Blob, voiceResponseEnabled: boolean = true, file?: File | null) => {
    const tempUserMsgId = generateId();
    addMessage({
      id: tempUserMsgId,
      text: "🎤 Sending audio...",
      isUser: true,
      timeStamp: Date.now(),
      ...(file ? { filename: file.name } : {}),
    });

    const botMsgId = generateId();
    addMessage({
      id: botMsgId,
      text: "",
      isUser: false,
      timeStamp: Date.now(),
      isLoading: true,
    });

    try {
      let docId = activeDocumentId;
      if (file) {
        const uploadRes = await uploadFile(file);
        docId = uploadRes.document_id;
        setActiveDocumentId(docId);
      }

      const response = await sendVoiceChat(audioBlob, voiceResponseEnabled, docId);

      setMessages((prev) =>
        prev.map((m) =>
            m.id === tempUserMsgId
            ? { ...m, text: response.transcribed_text || "🎤 [Audio Message]" }
            : m
        )
      );

      const botText = parseBackendResponse(JSON.stringify({ response: response.chat_response }));

      setMessages((prev) =>
        prev.map((m) =>
          m.id === botMsgId
            ? {
                ...m,
                text: botText,
                audioUrl: response.audio_url,
                isLoading: false
              }
            : m
        )
      );

      if (voiceResponseEnabled && !response.audio_url && response.chat_response) {
        const lang = response.detected_language === 'hi' ? 'hi-IN' : 'en-IN';
        speakWithBrowser(response.chat_response, lang);
      }
    } catch (err) {
      console.error("Voice Chat Error:", err);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === botMsgId 
          ? { ...m, text: "Error processing voice message.", isLoading: false } 
          : m
        )
      );
    }
  };

  const restoreSession = (userText: string, botText: string, audioUrl?: string) => {
    const userMsgId = generateId();
    const botMsgId = generateId();
    const now = Date.now();

    const restoredMessages: ChatMessage[] = [
      {
        id: userMsgId,
        text: userText,
        isUser: true,
        timeStamp: now,
      },
      {
        id: botMsgId,
        text: botText,
        isUser: false,
        timeStamp: now + 1,
        audioUrl: audioUrl,
        isLoading: false,
      },
    ];

    setMessages((prev) => [...prev, ...restoredMessages]);
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
    sendVoiceMessage, 
    containerRef, 
    regenerateMessage,
    setDocumentId,
    restoreSession
  };
}