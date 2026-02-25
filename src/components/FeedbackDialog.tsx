import { useState } from "react";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "./ui/dialog";
import { Textarea } from "./ui/textarea";
import { MessageSquare } from "lucide-react";
import { projectId } from "../utils/supabase/info";
import { toast } from "sonner@2.0.3";

interface FeedbackDialogProps {
  accessToken: string;
}

export function FeedbackDialog({ accessToken }: FeedbackDialogProps) {
  const [feedbackContent, setFeedbackContent] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  const handleSubmit = async () => {
    if (!feedbackContent.trim()) {
      toast.error("피드백 내용을 입력해주세요.");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await fetch(
        `https://${projectId}.supabase.co/functions/v1/make-server-f876292a/general-feedback`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${accessToken}`,
          },
          body: JSON.stringify({
            content: feedbackContent,
            type: "general",
          }),
        }
      );

      if (response.ok) {
        toast.success("피드백이 전송되었습니다. 감사합니다!");
        setFeedbackContent("");
        setIsOpen(false);
      } else {
        const data = await response.json();
        toast.error(data.error || "피드백 전송에 실패했습니다.");
      }
    } catch (error) {
      console.error("Failed to submit feedback:", error);
      toast.error("피드백 전송 중 오류가 발생했습니다.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button
          size="lg"
          className="fixed bottom-6 right-6 rounded-full shadow-lg gap-2 px-6 py-6 bg-blue-600 hover:bg-blue-700 z-50"
        >
          <MessageSquare className="w-5 h-5" />
          피드백 보내기
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>피드백 보내기</DialogTitle>
          <DialogDescription>
            서비스 개선을 위한 의견을 들려주세요. 모든 피드백은 소중하게 검토됩니다.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <Textarea
            placeholder="개선 사항, 버그, 의견 등을 자유롭게 작성��주세요..."
            value={feedbackContent}
            onChange={(e) => setFeedbackContent(e.target.value)}
            className="min-h-[150px] resize-none"
          />
          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => setIsOpen(false)}
              disabled={isSubmitting}
            >
              취소
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={isSubmitting || !feedbackContent.trim()}
            >
              {isSubmitting ? "전송 중..." : "전송"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
