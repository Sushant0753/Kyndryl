"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useChatMessage } from "@/hooks/useChatMessage";
import { ChatMessage } from "@/types/chat";
import ChatInput from "@/components/ChatInput";
import { FiFileText } from "react-icons/fi";
import { MdReplay } from "react-icons/md";
import { FaRegCopy } from "react-icons/fa";
import { LuCheck } from "react-icons/lu";

export default function ChatPage() {
  const { sessionId } = useParams();

  const {
    messages,
    sendUserMessage,
    sendVoiceMessage,
    containerRef,
    regenerateMessage,
    setDocumentId,
    restoreSession
  } = useChatMessage();

  const [copiedStates, setCopiedStates] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const key = `first-message-${sessionId}`;
    const raw = sessionStorage.getItem(key);
    if (!raw) return;

    try {
      const parsed = JSON.parse(raw);

      if (parsed.type === "voice_result") {
        restoreSession(parsed.userText, parsed.botText, parsed.audioUrl);
      } else if (parsed.text) {
        sendUserMessage(
          parsed.text,
          null,
          undefined,
          parsed.filename,
          parsed.documentId
        );
      } else if (parsed.documentId) {
        // File uploaded without a question — just activate the document context
        setDocumentId(parsed.documentId);
      }
    } catch (err) {
      console.error("Failed to restore initial message:", err);
    } finally {
      sessionStorage.removeItem(key);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const copyMessage = (text: string, id: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedStates((s) => ({ ...s, [id]: true }));
      setTimeout(() => {
        setCopiedStates((s) => ({ ...s, [id]: false }));
      }, 1500);
    });
  };

  return (
    <div className="flex flex-col h-screen bg-dots">
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto overflow-x-hidden px-4 py-6 space-y-4 pl-32 pr-16 w-full"
      >
        {messages.map((msg: ChatMessage) => (
          <div
            key={msg.id}
            className={`flex ${msg.isUser ? "justify-end" : "justify-start"}`}
          >
            <div className={`max-w-[80%] ${msg.isUser ? "" : "space-y-2"}`}>
              {msg.isLoading ? (
                <div className="flex gap-6 animate-pulse">
                  <div className="bg-neutral-800 rounded-2xl p-4 shadow-sm flex items-center">
                    <div className="flex space-x-2">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                      <div
                        className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                        style={{ animationDelay: "150ms" }}
                      />
                      <div
                        className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                        style={{ animationDelay: "300ms" }}
                      />
                    </div>
                  </div>
                </div>
              ) : (
                <div
                  className={`rounded-2xl px-4 py-2 shadow break-words ${
                    msg.isUser
                      ? "bg-blue-600 text-white"
                      : "bg-neutral-800 text-neutral-200 inline-block"
                  }`}
                >
                  <p
                    className="whitespace-pre-wrap break-words"
                    dangerouslySetInnerHTML={{ __html: msg.text }}
                  />

                  {msg.audioUrl && (
                    <div className="mt-3 bg-neutral-900/50 p-2 rounded-lg">
                      <audio
                        autoPlay
                        controls
                        src={msg.audioUrl}
                        className="w-full h-8 max-w-[250px]"
                      />
                    </div>
                  )}

                  {msg.filename && msg.isUser && (
                    <div className="inline-flex items-center gap-2 text-sm text-neutral-200 mt-2 bg-neutral-700 px-2 py-2 rounded-full shadow max-w-48">
                      <FiFileText size={16} className="text-neutral-300" />
                      <span className="truncate flex-1 pr-6">
                        {msg.filename}
                      </span>
                    </div>
                  )}
                </div>
              )}

              {!msg.isUser && !msg.isLoading && (
                <>
                  <div className="flex gap-2 pl-2">
                    <button
                      className="bg-transparent hover:bg-neutral-700/50 text-neutral-400 hover:text-neutral-200 p-2 rounded-lg transition-all cursor-pointer"
                      onClick={() => regenerateMessage(msg)}
                      title="Regenerate message"
                    >
                      <MdReplay size={16} />
                    </button>

                    <button
                      className="bg-transparent hover:bg-neutral-700/50 text-neutral-400 hover:text-neutral-200 p-2 rounded-lg transition-all cursor-pointer flex items-center gap-1"
                      onClick={() => copyMessage(msg.text, msg.id)}
                      title="Copy message"
                    >
                      {copiedStates[msg.id] ? (
                        <>
                          <LuCheck size={16} />
                          <span className="text-xs">Copied</span>
                        </>
                      ) : (
                        <FaRegCopy size={16} />
                      )}
                    </button>
                  </div>

                  <div className="pl-2 mt-1">
                    <p className="text-xs text-neutral-500 italic">
                      This AI can make mistakes. Please double-check responses.
                    </p>
                  </div>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
      <div className="p-4">
        <ChatInput
          sendUserMessage={(text, file, ttsEnabled) => sendUserMessage(text, file, ttsEnabled)}
          sendVoiceMessage={sendVoiceMessage}
        />
      </div>
    </div>
  );
}
