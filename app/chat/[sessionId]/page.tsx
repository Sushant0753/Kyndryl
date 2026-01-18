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
  const { messages, sendUserMessage, containerRef, regenerateMessage, setDocumentId } =
    useChatMessage();
  const [copiedStates, setCopiedStates] = useState<Record<string, boolean>>({});

  // Restore session from Home page
  useEffect(() => {
    const key = `first-message-${sessionId}`;
    const raw = sessionStorage.getItem(key);
    if (!raw) return;

    try {
      const parsed = JSON.parse(raw);
      
      // If we have an ID from the Home upload, pass it explicitly to the first message
      // This ensures the first request uses the ID immediately without waiting for state updates
      if (parsed.text) {
        sendUserMessage(
          parsed.text, 
          null, // No new file object (it's already on server)
          parsed.filename, // Pass filename string for UI chip
          parsed.documentId // Pass ID explicitly for this call
        );
      } else if (parsed.documentId) {
        // If there was no text (edge case), just set the ID
        setDocumentId(parsed.documentId);
      }
      
    } catch (err) {
      console.error("Failed to restore initial message:", err);
    } finally {
      sessionStorage.removeItem(key);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]); // Run once on mount

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
      {/* Chat messages */}
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
              {/* Message Bubble */}
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
                ></p>

                {/* File chip (Only for User messages with filename) */}
                {msg.filename && msg.isUser && (
                  <div className="inline-flex items-center gap-2 text-sm text-neutral-200 mt-2 bg-neutral-700 px-2 py-2 rounded-full shadow max-w-48">
                    <FiFileText size={16} className="text-neutral-300" />
                    <span className="truncate flex-1 pr-6">{msg.filename}</span>
                  </div>
                )}
              </div>

              {/* Assistant-only actions (Copy/Regenerate) */}
              {!msg.isUser && (
                <>
                  <div className="flex gap-2 pl-2">
                    {/* Regenerate */}
                    <button
                      className="bg-transparent hover:bg-neutral-700/50 text-neutral-400 hover:text-neutral-200 p-2 rounded-lg transition-all cursor-pointer"
                      onClick={() => regenerateMessage(msg)}
                      title="Regenerate message"
                    >
                      <MdReplay size={16} />
                    </button>

                    {/* Copy */}
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

      {/* Chat Input */}
      <div className="p-4">
        {/* Pass sendUserMessage directly. 
            ChatInput typically sends (text, file). 
            Our hook handles (text, file) correctly. */}
        <ChatInput sendUserMessage={(text, file) => sendUserMessage(text, file)} />
      </div>
    </div>
  );
}