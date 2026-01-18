export type ChatMessage = {
  id: string;
  text: string;
  isUser: boolean;
  timeStamp: number;
  documentId?: string;
  filename?: string;
};

export type ChatSummary = {
  id: string;
  userId: string;
  title: string;
  lastUpdated: number;
  createdAt: number;
};
