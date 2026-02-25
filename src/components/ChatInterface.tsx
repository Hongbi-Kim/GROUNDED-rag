import { useState, useEffect, useRef } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { ScrollArea } from "./ui/scroll-area";
import { Card } from "./ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "./ui/dialog";
import { Send, Building2, Home, HelpCircle, MessageSquare, FileText, Sparkles, ThumbsUp, ThumbsDown, RotateCcw } from "lucide-react";
import { projectId } from "../utils/supabase/info";

interface Message {
  id: string;
  type: "user" | "bot";
  content: string;
  timestamp: Date;
  references?: DocumentReference[];
}

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

interface ChatInterfaceProps {
  onDocumentReferenceClick: (reference: DocumentReference) => void;
  onGoHome?: () => void;
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  accessToken?: string;
  conversationId?: string;
  onMessagesChange?: () => void;
  isQuickQuestionMode?: boolean;
}

export function ChatInterface({ 
  onDocumentReferenceClick, 
  onGoHome, 
  messages, 
  setMessages,
  accessToken,
  conversationId,
  onMessagesChange,
  isQuickQuestionMode = false
}: ChatInterfaceProps) {
  const apiBase = (import.meta as any).env?.VITE_AGENT_API_BASE || "";
  const askApiUrl = apiBase ? `${apiBase}/api/v1/chat/ask` : "/api/v1/chat/ask";
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [progressMessages, setProgressMessages] = useState<string[]>([]);
  const [feedbackStates, setFeedbackStates] = useState<Record<string, 'positive' | 'negative' | null>>({});
  const [isLoadingQuestions, setIsLoadingQuestions] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom when messages change
  useEffect(() => {
    // Use setTimeout to ensure DOM is updated
    setTimeout(() => {
      if (messagesEndRef.current) {
        messagesEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
      }
      
      // Also try to scroll the viewport directly
      const viewport = scrollAreaRef.current?.querySelector('[data-slot="scroll-area-viewport"]');
      if (viewport) {
        viewport.scrollTop = viewport.scrollHeight;
      }
    }, 100);
  }, [messages]);

  // Load quick questions when entering quick question mode
  useEffect(() => {
    if (isQuickQuestionMode && accessToken) {
      loadQuickQuestions();
    }
  }, [isQuickQuestionMode, accessToken]);

  const loadQuickQuestions = async () => {
    if (!accessToken) return;

    setIsLoadingQuestions(true);
    try {
      const response = await fetch(
        `https://${projectId}.supabase.co/functions/v1/make-server-f876292a/quick-questions`,
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        const loadedMessages: Message[] = [];
        
        for (const q of data.questions) {
          // Add question message
          loadedMessages.push({
            id: q.id + "-question",
            type: "user",
            content: q.question,
            timestamp: new Date(q.timestamp),
          });
          
          // Add answer message
          loadedMessages.push({
            id: q.id,
            type: "bot",
            content: q.answer,
            timestamp: new Date(q.timestamp),
            references: [],
          });
          
          // Set feedback if exists
          if (q.feedback) {
            setFeedbackStates(prev => ({ ...prev, [q.id]: q.feedback }));
          }
        }
        
        setMessages(loadedMessages);
      }
    } catch (error) {
      console.error("Failed to load quick questions:", error);
    } finally {
      setIsLoadingQuestions(false);
    }
  };

  const saveQuickQuestion = async (questionId: string, question: string, answer: string) => {
    if (!accessToken) {
      // If not logged in, don't save to backend (just keep in local state)
      return;
    }

    try {
      await fetch(
        `https://${projectId}.supabase.co/functions/v1/make-server-f876292a/quick-question`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${accessToken}`,
          },
          body: JSON.stringify({
            questionId,
            question,
            answer,
            timestamp: new Date().toISOString(),
          }),
        }
      );
    } catch (error) {
      console.error("Failed to save quick question:", error);
    }
  };

  const handleClearQuickQuestions = () => {
    setMessages([]);
    setFeedbackStates({});
  };



  const handleFeedback = async (messageId: string, rating: 'positive' | 'negative') => {
    if (!accessToken) return;

    // Update UI immediately
    setFeedbackStates(prev => ({ ...prev, [messageId]: rating }));

    try {
      // If in quick question mode, save to quick question feedback
      if (isQuickQuestionMode) {
        await fetch(
          `https://${projectId}.supabase.co/functions/v1/make-server-f876292a/quick-question-feedback`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${accessToken}`,
            },
            body: JSON.stringify({
              questionId: messageId,
              rating,
            }),
          }
        );
      } else if (!conversationId) {
        // For non-conversation messages, save as general feedback
        const message = messages.find(m => m.id === messageId);
        await fetch(
          `https://${projectId}.supabase.co/functions/v1/make-server-f876292a/general-feedback`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${accessToken}`,
            },
            body: JSON.stringify({
              content: `피드백 (${rating}): ${message?.content || ''}`,
              type: 'quick_question_feedback',
            }),
          }
        );
      } else {
        // Save to conversation
        await fetch(
          `https://${projectId}.supabase.co/functions/v1/make-server-f876292a/feedback`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${accessToken}`,
            },
            body: JSON.stringify({
              messageId,
              conversationId,
              rating,
            }),
          }
        );
      }
    } catch (error) {
      console.error("Failed to save feedback:", error);
    }
  };

  // Load feedback states for current messages (feedback is now embedded in message)
  useEffect(() => {
    if (!messages.length) return;

    const feedbacks: Record<string, 'positive' | 'negative' | null> = {};
    
    for (const message of messages) {
      if (message.type === 'bot' && (message as any).feedback) {
        feedbacks[message.id] = (message as any).feedback.rating;
      }
    }

    setFeedbackStates(feedbacks);
  }, [messages]);

  const handleSend = () => {
    if (!inputValue.trim()) return;
    
    // Check if conversation exists (only for chat mode, not quick question mode)
    if (!conversationId && !isQuickQuestionMode) {
      return;
    }

    const questionId = Date.now().toString();
    const userQuestion = inputValue;

    const userMessage: Message = {
      id: questionId + "-question",
      type: "user",
      content: userQuestion,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsTyping(true);
    setProgressMessages([]);

    const runPipeline = async () => {
      const fallbackSteps = [
        "질문을 분류하고 있습니다...",
        "0-hop 관련 문서를 찾고 있습니다...",
        "현재 근거만으로 답변 가능한지 판단하고 있습니다...",
        "필요한 경우에만 참조 법령/조항을 확장하고 있습니다...",
        "최종 답변을 생성하고 있습니다...",
      ];

      try {
        for (const step of fallbackSteps) {
          setProgressMessages((prev) => [...prev, step]);
          await new Promise((resolve) => setTimeout(resolve, 220));
        }

        const response = await fetch(askApiUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            query: userQuestion,
            k: 5,
          }),
        });

        if (!response.ok) {
          const err = await response.text();
          throw new Error(err || `HTTP ${response.status}`);
        }

        const data = await response.json();
        if (Array.isArray(data.steps) && data.steps.length > 0) {
          setProgressMessages(data.steps);
        }
        const refs: DocumentReference[] = (data.references || []).map((ref: any) => ({
          documentName: ref.document_name || ref.law_name || "법령",
          section: ref.section || "",
          chunkKey: ref.chunk_key || "",
          contentPreview: ref.content_preview || "",
          fullText: ref.full_text || "",
          internalRefs: ref.internal_refs || [],
          externalRefs: ref.external_refs || [],
        }));

        const botAnswer = data.answer || "답변을 생성하지 못했습니다.";
        const botMessage: Message = {
          id: questionId,
          type: "bot",
          content:
            botAnswer +
            (data.trace?.expand_reason
              ? `\n\n[추적판단] ${String(data.trace.expand_reason)}`
              : ""),
          timestamp: new Date(),
          references: refs,
        };
        setMessages((prev) => [...prev, botMessage]);

        if (isQuickQuestionMode) {
          saveQuickQuestion(questionId, userQuestion, botAnswer);
        }
      } catch (error) {
        const reason =
          error instanceof TypeError
            ? `네트워크 연결 실패(백엔드 서버 확인 필요): ${askApiUrl}`
            : String(error);
        const botMessage: Message = {
          id: questionId,
          type: "bot",
          content: `요청 처리 중 오류가 발생했습니다: ${reason}`,
          timestamp: new Date(),
          references: [],
        };
        setMessages((prev) => [...prev, botMessage]);
      } finally {
        setIsTyping(false);
        setProgressMessages([]);
      }
    };

    runPipeline();
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 p-4 border-b bg-white">
        <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-blue-600">
          <Building2 className="w-6 h-6 text-white" />
        </div>
        <div className="flex-1">
          <h2>건축법률 AI 어시스턴트</h2>
          <p className="text-sm text-gray-500">
            {isQuickQuestionMode ? "빠른 질문하기" : "건축 관련 법규 질의응답"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Clear Button (Quick Question Mode Only) */}
          {isQuickQuestionMode && messages.length > 0 && (
            <Button 
              variant="ghost" 
              size="sm"
              onClick={handleClearQuickQuestions}
              className="gap-2"
            >
              <RotateCcw className="w-4 h-4" />
              초기화
            </Button>
          )}

          {/* Help Button */}
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="ghost" size="icon">
                <HelpCircle className="w-5 h-5" />
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[80vh]">
              <DialogHeader>
                <DialogTitle>사용 방법</DialogTitle>
                <DialogDescription>
                  건축법률 AI 어시스턴트 사용 가이드
                </DialogDescription>
              </DialogHeader>
              <ScrollArea className="h-[60vh] pr-4">
                <div className="space-y-6">
                  {/* How to use */}
                  <div className="space-y-3">
                    <h3 className="text-gray-900">기본 사용법</h3>
                    <ol className="text-sm text-gray-600 space-y-2 list-decimal list-inside">
                      {!isQuickQuestionMode ? (
                        <>
                          <li>좌측 사이드바에서 "새로운 대화" 버튼을 눌러 대화방을 생성하세요</li>
                          <li>하단 입력창에 건축 관련 법규 질문을 입력하세요</li>
                          <li>AI가 관련 법률 조항을 찾아 답변을 제공합니다</li>
                          <li>답변에 포함된 참고 문서를 클릭하면 우측 뷰어에서 확인할 수 있습니다</li>
                          <li>좌측 사이드바에서 이전 대화를 선택하거나 새 대화를 시작할 수 있습니다</li>
                          <li>AI 답변에 대해 좋아요/싫어요 피드백을 남길 수 있습니다</li>
                          <li>최대 3개의 대화방을 만들 수 있습니다</li>
                        </>
                      ) : (
                        <>
                          <li>하단 입력창에 건축 관련 법규 질문을 입력하세요</li>
                          <li>AI가 관련 법률 조항을 찾아 답변을 제공합니다</li>
                          <li>답변에 포함된 참고 문서를 클릭하면 우측 뷰어에서 확인할 수 있습니다</li>
                          <li>질문하기 모드는 일회성이며 대화 내용이 저장되지 않습니다</li>
                          <li>대화 내용을 저장하려면 "채팅하기"를 이용하세요</li>
                        </>
                      )}
                    </ol>
                  </div>

                  {/* Example Questions */}
                  <div className="space-y-3">
                    <h3 className="text-gray-900">질문 예시</h3>
                    <div className="space-y-2">
                      <Card className="p-3 bg-gray-50 border-gray-200">
                        <p className="text-sm text-gray-700">"주택 건축 시 건폐율 기준은 어떻게 되나요?"</p>
                      </Card>
                      <Card className="p-3 bg-gray-50 border-gray-200">
                        <p className="text-sm text-gray-700">"상업지역 건축물 높이 제한은?"</p>
                      </Card>
                      <Card className="p-3 bg-gray-50 border-gray-200">
                        <p className="text-sm text-gray-700">"건축 허가 신청 시 필요한 서류는?"</p>
                      </Card>
                    </div>
                  </div>

                  {/* Features */}
                  <div className="space-y-3">
                    <h3 className="text-gray-900">주요 기능</h3>
                    <div className="space-y-3">
                      <div className="flex gap-3">
                        <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center shrink-0">
                          <MessageSquare className="w-4 h-4 text-blue-600" />
                        </div>
                        <div>
                          <p className="text-sm">실시간 대화형 질의응답</p>
                          <p className="text-xs text-gray-500">자연어로 편하게 질문하세요</p>
                        </div>
                      </div>
                      <div className="flex gap-3">
                        <div className="w-8 h-8 rounded-lg bg-green-100 flex items-center justify-center shrink-0">
                          <FileText className="w-4 h-4 text-green-600" />
                        </div>
                        <div>
                          <p className="text-sm">법률 문서 뷰어</p>
                          <p className="text-xs text-gray-500">참고 조항을 바로 확인</p>
                        </div>
                      </div>
                      <div className="flex gap-3">
                        <div className="w-8 h-8 rounded-lg bg-purple-100 flex items-center justify-center shrink-0">
                          <Sparkles className="w-4 h-4 text-purple-600" />
                        </div>
                        <div>
                          <p className="text-sm">AI 기반 정확한 답변</p>
                          <p className="text-xs text-gray-500">신뢰할 수 있는 정보 제공</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Tips */}
                  <div className="space-y-3">
                    <h3 className="text-gray-900">유용한 팁</h3>
                    <ul className="text-sm text-gray-600 space-y-2 list-disc list-inside">
                      <li>구체적으로 질문할수록 더 정확한 답변을 받을 수 있습니다</li>
                      <li>여러 질문을 한 번에 하기보다 하나씩 질문하세요</li>
                      <li>참고 문서는 클릭하여 원문을 확인할 수 있습니다</li>
                      {!isQuickQuestionMode && <li>대화방은 자동으로 클라우드에 저장됩니다</li>}
                      {!isQuickQuestionMode && <li>피드백을 통해 AI 답변 품질 향상에 기여할 수 있습니다</li>}
                    </ul>
                  </div>
                </div>
              </ScrollArea>
            </DialogContent>
          </Dialog>

          {/* Home Button */}
          {onGoHome && (
            <Button variant="ghost" size="icon" onClick={onGoHome}>
              <Home className="w-5 h-5" />
            </Button>
          )}
        </div>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 p-4" ref={scrollAreaRef}>
        <div className="space-y-4 pb-4">
          {isLoadingQuestions && (
            <div className="flex flex-col items-center justify-center h-full py-12">
              <div className="flex gap-1 mb-4">
                <span className="w-3 h-3 bg-blue-600 rounded-full animate-bounce" />
                <span
                  className="w-3 h-3 bg-blue-600 rounded-full animate-bounce"
                  style={{ animationDelay: "0.1s" }}
                />
                <span
                  className="w-3 h-3 bg-blue-600 rounded-full animate-bounce"
                  style={{ animationDelay: "0.2s" }}
                />
              </div>
              <p className="text-sm text-gray-600">이전 질문 기록을 불러오는 중...</p>
            </div>
          )}
          {!isLoadingQuestions && messages.length === 0 && !conversationId && !isQuickQuestionMode && (
            <div className="flex flex-col items-center justify-center h-full py-12 text-center">
              <Building2 className="w-16 h-16 text-blue-200 mb-4" />
              <h3 className="text-gray-700 mb-2">건축법률 AI 어시스턴트</h3>
              <p className="text-sm text-gray-500 mb-6 max-w-md">
                건축 관련 법률문서 기반 질의응답 시스템입니다.<br />
                왼쪽 사이드바에서 "새로운 대화"를 만들어 시작하세요.
              </p>
              <div className="text-xs text-gray-400 space-y-1">
                <p>💡 최대 3개의 대화방을 만들 수 있습니다</p>
                <p>💾 모든 대화는 자동으로 저장됩니다</p>
              </div>
            </div>
          )}
          {!isLoadingQuestions && messages.length === 0 && isQuickQuestionMode && (
            <div className="flex flex-col items-center justify-center h-full py-12 px-4">
              <div className="max-w-3xl w-full space-y-8">
                {/* Header */}
                <div className="text-center space-y-3">
                  <div className="flex justify-center mb-4">
                    <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center shadow-lg">
                      <Building2 className="w-10 h-10 text-white" />
                    </div>
                  </div>
                  <h2 className="text-gray-900">건축법률에 대해 무엇이든 물어보세요</h2>
                  <p className="text-gray-600">
                    AI가 관련 법률 조항을 찾아 정확한 답변을 제공합니다
                  </p>
                </div>

                {/* Example Questions */}
                <div className="space-y-3">
                  <p className="text-sm text-gray-700 text-center">예시 질문:</p>
                  <div className="grid gap-3">
                    <Card 
                      className="p-4 bg-white border-2 border-gray-200 hover:border-blue-300 hover:bg-blue-50/50 cursor-pointer transition-all"
                      onClick={() => setInputValue("주택 건축 시 건폐율 기준은 어떻게 되나요?")}
                    >
                      <div className="flex items-start gap-3">
                        <MessageSquare className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
                        <div>
                          <p className="text-sm">주택 건축 시 건폐율 기준은 어떻게 되나요?</p>
                        </div>
                      </div>
                    </Card>
                    <Card 
                      className="p-4 bg-white border-2 border-gray-200 hover:border-blue-300 hover:bg-blue-50/50 cursor-pointer transition-all"
                      onClick={() => setInputValue("상업지역 건축물 높이 제한은?")}
                    >
                      <div className="flex items-start gap-3">
                        <MessageSquare className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
                        <div>
                          <p className="text-sm">상업지역 건축물 높이 제한은?</p>
                        </div>
                      </div>
                    </Card>
                    <Card 
                      className="p-4 bg-white border-2 border-gray-200 hover:border-blue-300 hover:bg-blue-50/50 cursor-pointer transition-all"
                      onClick={() => setInputValue("건축 허가 신청 시 필요한 서류는?")}
                    >
                      <div className="flex items-start gap-3">
                        <MessageSquare className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
                        <div>
                          <p className="text-sm">건축 허가 신청 시 필요한 서류는?</p>
                        </div>
                      </div>
                    </Card>
                  </div>
                </div>

                {/* Info */}
                <div className="bg-blue-50 rounded-xl p-4 border border-blue-100">
                  <div className="flex gap-3">
                    <Sparkles className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
                    <div className="space-y-1">
                      <p className="text-sm text-blue-900">빠른 질문 모드</p>
                      <p className="text-xs text-blue-700">
                        {accessToken 
                          ? "질문-답변 내역이 자동으로 저장됩니다. 화면을 초기화하려면 우측 상단의 \"초기화\" 버튼을 누르세요."
                          : "로그인하지 않은 상태입니다. 질문-답변은 현재 세션에만 유지되며 저장되지 않습니다. 화면을 초기화하려면 우측 상단의 \"초기화\" 버튼을 누르세요."
                        }
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
          {messages.map((message, index) => (
            <div key={message.id}>
              <div
                className={`flex ${message.type === "user" ? "justify-end" : "justify-start items-start"}`}
              >
                <div
                  className={`max-w-[80%] ${
                    message.type === "user"
                      ? "bg-blue-600 text-white rounded-2xl rounded-tr-sm"
                      : "bg-gray-100 text-gray-900 rounded-2xl rounded-tl-sm"
                  } px-4 py-3`}
                >
                  <p className="whitespace-pre-wrap">{message.content}</p>
                  {message.references && message.references.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-200 space-y-2">
                      <p className="text-xs text-gray-600">참고 문서:</p>
                      {message.references.map((ref, refIndex) => (
                        <Button
                          key={refIndex}
                          variant="outline"
                          size="sm"
                          className="w-full justify-start text-left bg-white hover:bg-gray-50"
                          onClick={() => onDocumentReferenceClick(ref)}
                        >
                          <div className="flex flex-col items-start gap-1">
                            <span className="text-xs">{ref.documentName}</span>
                            <span className="text-xs text-gray-500">
                              {ref.section}
                              {ref.page && ` • ${ref.page}페이지`}
                            </span>
                          </div>
                        </Button>
                      ))}
                    </div>
                  )}
                  <p className="text-xs mt-2 opacity-70">
                    {message.timestamp.toLocaleTimeString("ko-KR", {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>
                
                {/* Feedback buttons for bot messages */}
                {message.type === "bot" && accessToken && (
                  <div className="flex gap-1 ml-2">
                    <Button
                      variant="ghost"
                      size="icon"
                      className={`h-8 w-8 ${
                        feedbackStates[message.id] === 'positive' 
                          ? 'text-green-600 bg-green-50' 
                          : 'text-gray-400 hover:text-green-600'
                      }`}
                      onClick={() => handleFeedback(message.id, 'positive')}
                    >
                      <ThumbsUp className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className={`h-8 w-8 ${
                        feedbackStates[message.id] === 'negative' 
                          ? 'text-red-600 bg-red-50' 
                          : 'text-gray-400 hover:text-red-600'
                        }`}
                      onClick={() => handleFeedback(message.id, 'negative')}
                    >
                      <ThumbsDown className="w-4 h-4" />
                    </Button>
                  </div>
                )}
              </div>
              
              {/* Separator for Q&A sets in quick question mode */}
              {isQuickQuestionMode && message.type === "bot" && index < messages.length - 1 && (
                <div className="my-6 flex items-center gap-3">
                  <div className="flex-1 h-px bg-gradient-to-r from-transparent via-gray-300 to-transparent" />
                  <span className="text-xs text-gray-400 px-2">새로운 질문</span>
                  <div className="flex-1 h-px bg-gradient-to-r from-transparent via-gray-300 to-transparent" />
                </div>
              )}
            </div>
          ))}
          {isTyping && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-2xl rounded-tl-sm px-4 py-3 space-y-2">
                <div className="flex gap-1 mb-1">
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0.1s" }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }} />
                </div>
                {progressMessages.length > 0 && (
                  <div className="space-y-1">
                    {progressMessages.map((msg, idx) => (
                      <p key={`${msg}-${idx}`} className="text-xs text-gray-600">
                        {msg}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      {/* Input Area */}
      <div className="p-4 border-t bg-white">
        {!conversationId && !isQuickQuestionMode ? (
          <div className="text-center py-4 space-y-2">
            <p className="text-sm text-gray-600">
              대화를 시작하려면 왼쪽에서 <span className="font-medium text-blue-600">"새로운 대화"</span>를 만들어주세요.
            </p>
            <p className="text-xs text-gray-500">
              최대 3개의 대화방을 만들 수 있습니다.
            </p>
          </div>
        ) : (
          <>
            <div className="flex gap-2">
              <Input
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="건축 관련 법규에 대해 질문해주세요..."
                className="flex-1"
              />
              <Button onClick={handleSend} size="icon" className="shrink-0">
                <Send className="w-4 h-4" />
              </Button>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              예시: "주택 건축 시 건폐율 기준은?" "상업지역 건축물 높이 제한은?"
            </p>
          </>
        )}
      </div>
    </div>
  );
}
