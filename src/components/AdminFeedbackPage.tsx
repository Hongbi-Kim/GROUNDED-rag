import { useState, useEffect } from "react";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { ScrollArea } from "./ui/scroll-area";
import { ArrowLeft, Mail, Calendar, MessageSquare } from "lucide-react";
import { projectId } from "../utils/supabase/info";

interface Feedback {
  id: string;
  userId: string;
  userEmail: string;
  content: string;
  type: string;
  createdAt: string;
}

interface AdminFeedbackPageProps {
  accessToken: string;
  onBack: () => void;
}

export function AdminFeedbackPage({ accessToken, onBack }: AdminFeedbackPageProps) {
  const [feedbacks, setFeedbacks] = useState<Feedback[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadFeedbacks();
  }, []);

  const loadFeedbacks = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(
        `https://${projectId}.supabase.co/functions/v1/make-server-f876292a/admin/feedbacks`,
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setFeedbacks(data.feedbacks);
      } else {
        console.error("Failed to load feedbacks");
      }
    } catch (error) {
      console.error("Error loading feedbacks:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString("ko-KR", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <div className="bg-white border-b px-6 py-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={onBack}>
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-gray-900">피드백 관리</h1>
            <p className="text-sm text-gray-500">사용자 피드백 목록</p>
          </div>
        </div>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1 p-6">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <p className="text-gray-500">피드백을 불러오는 중...</p>
          </div>
        ) : feedbacks.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <MessageSquare className="w-16 h-16 text-gray-300 mb-4" />
            <h3 className="text-gray-700 mb-2">피드백이 없습니다</h3>
            <p className="text-sm text-gray-500">아직 등록된 피드백이 없습니다.</p>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto space-y-4">
            <div className="mb-6">
              <p className="text-sm text-gray-600">총 {feedbacks.length}개의 피드백</p>
            </div>
            {feedbacks.map((feedback) => (
              <Card key={feedback.id} className="p-6 bg-white">
                <div className="space-y-4">
                  {/* Header */}
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center gap-2 text-sm text-gray-600">
                        <Mail className="w-4 h-4" />
                        <span>{feedback.userEmail}</span>
                      </div>
                      <div className="flex items-center gap-2 text-sm text-gray-600">
                        <Calendar className="w-4 h-4" />
                        <span>{formatDate(feedback.createdAt)}</span>
                      </div>
                    </div>
                    <div className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs">
                      {feedback.type}
                    </div>
                  </div>

                  {/* Content */}
                  <div className="pt-3 border-t">
                    <p className="text-gray-800 whitespace-pre-wrap">{feedback.content}</p>
                  </div>

                  {/* Footer */}
                  <div className="pt-3 border-t text-xs text-gray-400">
                    ID: {feedback.id}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
