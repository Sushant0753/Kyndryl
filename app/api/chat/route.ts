import { NextRequest } from "next/server";
import { uploadedFiles } from "@/lib/fileStorage";

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const query = formData.get("query") as string;
    const document_id = formData.get("document_id") as string | null;

    if (!query) {
      return new Response(
        JSON.stringify({ error: "Query parameter is required" }),
        {
          status: 400,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    // Validate document_id if provided
    if (document_id && !uploadedFiles.has(document_id)) {
      return new Response(
        JSON.stringify({ error: "Invalid document_id" }),
        {
          status: 400,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    // Create a readable stream for SSE (Server-Sent Events)
    const encoder = new TextEncoder();
    
    const stream = new ReadableStream({
      async start(controller) {
        try {
          // Generate a simulated response
          // In a real implementation, this would call an AI service
          let response = "";
          
          if (document_id) {
            response = `I received your query: "${query}" with document ID: ${document_id}. `;
          } else {
            response = `I received your query: "${query}". `;
          }
          
          response += "This is a simulated AI assistant response. In a production environment, this would be connected to an actual AI/LLM service like OpenAI, Anthropic, or a local model to generate meaningful responses based on your query.";

          // Stream the response word by word to simulate typing effect
          const words = response.split(" ");
          for (let i = 0; i < words.length; i++) {
            const chunk = (i === 0 ? words[i] : " " + words[i]);
            controller.enqueue(encoder.encode(chunk));
            
            // Add a small delay to simulate streaming
            await new Promise((resolve) => setTimeout(resolve, 50));
          }
          
          controller.close();
        } catch (error) {
          console.error("Streaming error:", error);
          controller.error(error);
        }
      },
    });

    // Return streaming response
    return new Response(stream, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
      },
    });
  } catch (error) {
    console.error("Chat error:", error);
    return new Response(
      JSON.stringify({ error: "Internal server error during chat" }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}
