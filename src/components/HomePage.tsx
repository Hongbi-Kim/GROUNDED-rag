import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { WaveSpaceLogo } from "./WaveSpaceLogo";
import { ArrowRight, FileText, MessageSquare, Sparkles, HelpCircle, Shield, LogOut, UserX, LogIn } from "lucide-react";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "./ui/alert-dialog";

interface HomePageProps {
  onStartChat: () => void;
  onStartQuickQuestion: () => void;
  onShowAdminPage?: () => void;
  onShowLoginPage?: () => void;
  userEmail?: string | null;
  isLoggedIn?: boolean;
  onLogout: () => void;
  onDeleteAccount: () => void;
}

export function HomePage({ 
  onStartChat, 
  onStartQuickQuestion, 
  onShowAdminPage, 
  onShowLoginPage,
  userEmail, 
  isLoggedIn = false,
  onLogout, 
  onDeleteAccount 
}: HomePageProps) {
  const isAdmin = userEmail === "khb1620@naver.com";
  return (
    <div className="h-screen bg-gradient-to-br from-gray-50 via-blue-50/30 to-gray-50 flex items-center justify-center p-4 relative">
      {/* User Menu - Top Right */}
      <div className="absolute top-4 right-4 flex items-center gap-2">
        {isLoggedIn ? (
          <>
            <span className="text-sm text-gray-600">{userEmail}</span>
            <Button
              onClick={onLogout}
              size="sm"
              variant="outline"
              className="gap-2"
            >
              <LogOut className="w-4 h-4" />
              로그아웃
            </Button>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  size="sm"
                  variant="outline"
                  className="gap-2 border-red-300 text-red-600 hover:bg-red-50"
                >
                  <UserX className="w-4 h-4" />
                  회원 탈퇴
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>정말 회원 탈퇴하시겠습니까?</AlertDialogTitle>
                  <AlertDialogDescription>
                    이 작업은 되돌릴 수 없습니다. 계정과 모든 대화 기록이 영구적으로 삭제됩니다.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>취소</AlertDialogCancel>
                  <AlertDialogAction 
                    onClick={onDeleteAccount}
                    className="bg-red-600 hover:bg-red-700"
                  >
                    탈퇴하기
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </>
        ) : (
          <>
            <span className="text-sm text-gray-600">게스트 모드</span>
            {onShowLoginPage && (
              <Button
                onClick={onShowLoginPage}
                size="sm"
                variant="outline"
                className="gap-2"
              >
                <LogIn className="w-4 h-4" />
                로그인
              </Button>
            )}
          </>
        )}
      </div>

      <div className="max-w-4xl w-full">
        <div className="text-center space-y-8">
          {/* Logo and Title */}
          <div className="flex flex-col items-center gap-6">
            <div className="relative">
              <div className="absolute inset-0 bg-blue-500/20 blur-3xl rounded-full animate-pulse" />
              <WaveSpaceLogo size={120} animated={true} />
            </div>
            
            <div className="space-y-3">
              <h1 className="text-gray-900">건축법률 AI 어시스턴트</h1>
              <p className="text-gray-600 max-w-2xl mx-auto">
                건축 관련 법률문서 기반 질의응답 시스템으로, 복잡한 건축 법규를 쉽고 빠르게 이해할 수 있습니다.
                AI가 관련 법률 조항을 찾아 정확한 답변을 제공합니다.
              </p>
              {!isLoggedIn && (
                <p className="text-sm text-blue-600 bg-blue-50 border border-blue-200 rounded-lg px-4 py-2 max-w-xl mx-auto">
                  💡 로그인 없이도 질문하기 기능을 바로 사용할 수 있습니다. 대화 내용을 저장하려면 로그인하세요.
                </p>
              )}
            </div>
          </div>

          {/* Features */}
          <div className="grid md:grid-cols-3 gap-4 mt-12">
            <Card className="p-6 bg-white/80 backdrop-blur border-gray-200 hover:shadow-lg transition-shadow">
              <div className="flex flex-col items-center text-center gap-3">
                <div className="w-12 h-12 rounded-lg bg-blue-100 flex items-center justify-center">
                  <MessageSquare className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <h3 className="text-gray-900 mb-1">대화형 인터페이스</h3>
                  <p className="text-sm text-gray-600">
                    자연어로 질문하고 즉시 답변을 받아보세요
                  </p>
                </div>
              </div>
            </Card>

            <Card className="p-6 bg-white/80 backdrop-blur border-gray-200 hover:shadow-lg transition-shadow">
              <div className="flex flex-col items-center text-center gap-3">
                <div className="w-12 h-12 rounded-lg bg-green-100 flex items-center justify-center">
                  <FileText className="w-6 h-6 text-green-600" />
                </div>
                <div>
                  <h3 className="text-gray-900 mb-1">법률문서 뷰어</h3>
                  <p className="text-sm text-gray-600">
                    참고한 법률 조항을 실시간으로 확인하세요
                  </p>
                </div>
              </div>
            </Card>

            <Card className="p-6 bg-white/80 backdrop-blur border-gray-200 hover:shadow-lg transition-shadow">
              <div className="flex flex-col items-center text-center gap-3">
                <div className="w-12 h-12 rounded-lg bg-purple-100 flex items-center justify-center">
                  <Sparkles className="w-6 h-6 text-purple-600" />
                </div>
                <div>
                  <h3 className="text-gray-900 mb-1">AI 기반 분석</h3>
                  <p className="text-sm text-gray-600">
                    정확하고 신뢰할 수 있는 법률 정보 제공
                  </p>
                </div>
              </div>
            </Card>
          </div>

          {/* CTA Buttons */}
          <div className="pt-8 flex flex-col sm:flex-row gap-4 justify-center items-center">
            <Button
              onClick={onStartChat}
              size="lg"
              className="gap-2 px-8 py-6 bg-blue-600 hover:bg-blue-700 w-full sm:w-auto"
            >
              <MessageSquare className="w-5 h-5" />
              채팅하기
              <ArrowRight className="w-5 h-5" />
            </Button>
            <Button
              onClick={onStartQuickQuestion}
              size="lg"
              variant="outline"
              className="gap-2 px-8 py-6 border-2 border-blue-600 text-blue-600 hover:bg-blue-50 w-full sm:w-auto"
            >
              <HelpCircle className="w-5 h-5" />
              질문하기
            </Button>
          </div>

          {/* Admin Button */}
          {isAdmin && onShowAdminPage && (
            <div className="pt-4 flex justify-center">
              <Button
                onClick={onShowAdminPage}
                size="sm"
                variant="outline"
                className="gap-2 border-red-300 text-red-600 hover:bg-red-50"
              >
                <Shield className="w-4 h-4" />
                관리자 페이지
              </Button>
            </div>
          )}

          {/* Footer Info */}
          <p className="text-sm text-gray-500 pt-8">
            질문 예시: "주택 건축 시 건폐율 기준은?" • "상업지역 건축물 높이 제한은?"
          </p>
        </div>
      </div>
    </div>
  );
}