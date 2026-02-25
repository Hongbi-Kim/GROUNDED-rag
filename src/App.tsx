import { useState } from "react";
import { HomePage } from "./components/HomePage";
import { ChatInterface } from "./components/ChatInterface";
import { DocumentViewer } from "./components/DocumentViewer";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "./components/ui/resizable";
import { Toaster } from "./components/ui/sonner";

interface DocumentReference {
  documentName: string;
  section: string;
  page?: number;
  chunkKey?: string;
  contentPreview?: string;
  fullText?: string;
  internalRefs?: Array<Record<string, unknown>>;
  externalRefs?: Array<Record<string, unknown>>;
}

interface Message {
  id: string;
  type: "user" | "bot";
  content: string;
  timestamp: Date;
  references?: DocumentReference[];
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [selectedReference, setSelectedReference] = useState<DocumentReference | null>(null);
  const [showHomePage, setShowHomePage] = useState(true);
  const [isQuickQuestionMode, setIsQuickQuestionMode] = useState(false);

  const handleStartChat = () => {
    setShowHomePage(false);
    setIsQuickQuestionMode(false);
    setMessages([]);
    setSelectedReference(null);
  };

  const handleStartQuickQuestion = () => {
    setShowHomePage(false);
    setIsQuickQuestionMode(true);
    setMessages([]);
    setSelectedReference(null);
  };

  const handleGoHome = () => {
    setShowHomePage(true);
    setIsQuickQuestionMode(false);
    setMessages([]);
    setSelectedReference(null);
  };

  const handleDocumentReferenceClick = (reference: DocumentReference) => {
    setSelectedReference(reference);
  };

  const handleCloseDocument = () => {
    setSelectedReference(null);
  };

  if (showHomePage) {
    return (
      <HomePage
        onStartChat={handleStartChat}
        onStartQuickQuestion={handleStartQuickQuestion}
        isLoggedIn={false}
        userEmail={null}
        onLogout={() => {}}
        onDeleteAccount={() => {}}
      />
    );
  }

  return (
    <>
      <div className="h-screen bg-gray-50 flex">
        <ResizablePanelGroup direction="horizontal" className="flex-1">
          <ResizablePanel defaultSize={50} minSize={30}>
            <div className="h-full bg-white border-r">
              <ChatInterface
                onDocumentReferenceClick={handleDocumentReferenceClick}
                onGoHome={handleGoHome}
                messages={messages}
                setMessages={setMessages}
                conversationId={isQuickQuestionMode ? undefined : "local-conversation"}
                isQuickQuestionMode={isQuickQuestionMode}
              />
            </div>
          </ResizablePanel>

          <ResizableHandle withHandle />

          <ResizablePanel defaultSize={50} minSize={30}>
            <div className="h-full">
              <DocumentViewer selectedReference={selectedReference} onClose={handleCloseDocument} />
            </div>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
      <Toaster />
    </>
  );
}
