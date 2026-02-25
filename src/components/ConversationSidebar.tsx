import { useState, useEffect } from "react";
import { Button } from "./ui/button";
import { ScrollArea } from "./ui/scroll-area";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "./ui/alert-dialog";
import { Plus, MessageSquare, Trash2, LogOut, User } from "lucide-react";
import { projectId, publicAnonKey } from "../utils/supabase/info";

interface Conversation {
  id: string;
  userId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
}

interface ConversationSidebarProps {
  accessToken: string;
  currentConversationId: string | null;
  onSelectConversation: (conversationId: string) => void;
  onNewConversation: () => Promise<boolean>;
  onLogout: () => void;
  userName?: string;
  onConversationsChange?: () => void;
}

export function ConversationSidebar({
  accessToken,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onLogout,
  userName,
  onConversationsChange,
}: ConversationSidebarProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadConversations = async () => {
    setIsLoading(true);
    try {
      console.log("Loading conversations...");
      const response = await fetch(
        `https://${projectId}.supabase.co/functions/v1/make-server-f876292a/conversations`,
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        }
      );

      console.log("Conversations response status:", response.status);
      const data = await response.json();
      console.log("Conversations data:", data);

      if (!response.ok) {
        throw new Error(data.error || "Failed to load conversations");
      }

      setConversations(data.conversations || []);
    } catch (error) {
      console.error("Failed to load conversations:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadConversations();
  }, [accessToken]);

  const handleDeleteConversation = async (conversationId: string) => {
    try {
      const response = await fetch(
        `https://${projectId}.supabase.co/functions/v1/make-server-f876292a/conversations/${conversationId}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        }
      );

      if (!response.ok) {
        const data = await response.json();
        console.error("Delete conversation error:", data);
        throw new Error(data.error || "Failed to delete conversation");
      }

      // If deleted conversation was selected, clear selection
      if (conversationId === currentConversationId) {
        // Find remaining conversations before reloading
        const remainingConversations = conversations.filter(c => c.id !== conversationId);
        if (remainingConversations.length > 0) {
          // Select the first remaining conversation
          onSelectConversation(remainingConversations[0].id);
        }
      }

      // Reload conversations list after selection
      await loadConversations();
    } catch (error) {
      console.error("Failed to delete conversation:", error);
    }
  };

  const handleNewConversation = async () => {
    await onNewConversation();
    // Reload conversations immediately to show the new one
    await loadConversations();
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "방금 전";
    if (diffMins < 60) return `${diffMins}분 전`;
    if (diffHours < 24) return `${diffHours}시간 전`;
    if (diffDays < 7) return `${diffDays}일 전`;
    
    return date.toLocaleDateString("ko-KR", { month: "short", day: "numeric" });
  };

  return (
    <div className="w-64 bg-gray-50 border-r flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b bg-white space-y-3">
        <div className="flex items-center gap-2 text-sm">
          <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
            <User className="w-4 h-4 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="truncate text-gray-900">{userName || "사용자"}</p>
          </div>
        </div>
        
        <div className="space-y-2">
          <Button 
            onClick={handleNewConversation} 
            className="w-full"
            disabled={conversations.length >= 3}
          >
            <Plus className="w-4 h-4" />
            새로운 대화
          </Button>
          <p className="text-xs text-gray-500 text-center">
            {conversations.length}/3 대화방
          </p>
        </div>
      </div>

      {/* Conversations List */}
      <ScrollArea className="flex-1">
        <div className="p-2 space-y-1">
          {isLoading ? (
            <div className="text-center py-8 text-sm text-gray-500">
              불러오는 중...
            </div>
          ) : conversations.length === 0 ? (
            <div className="text-center py-8 text-sm text-gray-500">
              대화 기록이 없습니다
            </div>
          ) : (
            conversations.map((conversation) => (
              <div
                key={conversation.id}
                className={`group relative flex items-center gap-2 p-3 rounded-lg cursor-pointer transition-colors ${
                  currentConversationId === conversation.id
                    ? "bg-blue-100 text-blue-900"
                    : "hover:bg-gray-100"
                }`}
                onClick={() => {
                  console.log("Selecting conversation:", conversation.id);
                  onSelectConversation(conversation.id);
                }}
              >
                <MessageSquare className="w-4 h-4 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm truncate">{conversation.title}</p>
                  <p className="text-xs text-gray-500">
                    {formatDate(conversation.updatedAt)}
                  </p>
                </div>
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="opacity-0 group-hover:opacity-100 shrink-0 h-7 w-7"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>대화 삭제</AlertDialogTitle>
                      <AlertDialogDescription>
                        이 대화를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>취소</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={() => handleDeleteConversation(conversation.id)}
                      >
                        삭제
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
            ))
          )}
        </div>
      </ScrollArea>

      {/* Logout Button at Bottom */}
      <div className="p-4 border-t bg-white">
        <Button 
          variant="outline" 
          onClick={onLogout} 
          className="w-full justify-start gap-2"
        >
          <LogOut className="w-4 h-4" />
          로그아웃
        </Button>
      </div>
    </div>
  );
}
