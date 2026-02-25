import { ScrollArea } from "./ui/scroll-area";
import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
import { FileText, X } from "lucide-react";
import { Button } from "./ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";

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

interface DocumentViewerProps {
  selectedReference: DocumentReference | null;
  onClose: () => void;
}

export function DocumentViewer({ selectedReference, onClose }: DocumentViewerProps) {
  const relatedRefs = [
    ...((selectedReference?.internalRefs || []).map((r) => ({ ...r, type: "internal" }))),
    ...((selectedReference?.externalRefs || []).map((r) => ({ ...r, type: "external" }))),
  ];

  if (!selectedReference) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-400 p-8">
        <FileText className="w-16 h-16 mb-4" />
        <p>참고 문서를 선택하면</p>
        <p>여기에 내용이 표시됩니다</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-3">
          <FileText className="w-5 h-5 text-blue-600" />
          <div>
            <h3>{selectedReference.documentName}</h3>
            <p className="text-sm text-gray-500">{selectedReference.section}</p>
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X className="w-4 h-4" />
        </Button>
      </div>

      {/* Content */}
      <Tabs defaultValue="full" className="flex-1 flex flex-col">
        <TabsList className="mx-4 mt-4 w-auto">
          <TabsTrigger value="full">전문</TabsTrigger>
          <TabsTrigger value="summary">요약</TabsTrigger>
          <TabsTrigger value="related">관련 조항</TabsTrigger>
        </TabsList>

        <TabsContent value="full" className="flex-1 mt-0">
          <ScrollArea className="h-full">
            <div className="p-6">
              {selectedReference.page && (
                <Badge variant="outline" className="mb-4">
                  {selectedReference.page}페이지
                </Badge>
              )}
              {selectedReference.chunkKey && (
                <Badge variant="outline" className="mb-4 ml-2">
                  {selectedReference.chunkKey}
                </Badge>
              )}
              <div className="prose prose-sm max-w-none">
                <pre className="whitespace-pre-wrap font-sans text-gray-700 leading-relaxed">
                  {selectedReference.fullText || selectedReference.contentPreview || "본문이 없습니다."}
                </pre>
              </div>
            </div>
          </ScrollArea>
        </TabsContent>

        <TabsContent value="summary" className="flex-1 mt-0">
          <ScrollArea className="h-full">
            <div className="p-6">
              <Card className="p-4 bg-blue-50 border-blue-200">
                <h4 className="text-sm mb-2 text-blue-900">조항 요약</h4>
                <p className="text-sm text-blue-800">
                  {selectedReference.contentPreview || "요약 정보가 없습니다."}
                </p>
              </Card>
            </div>
          </ScrollArea>
        </TabsContent>

        <TabsContent value="related" className="flex-1 mt-0">
          <ScrollArea className="h-full">
            <div className="p-6 space-y-3">
              {relatedRefs.length === 0 && (
                <Card className="p-4">
                  <p className="text-sm text-gray-500">관련 참조 정보가 없습니다.</p>
                </Card>
              )}
              {relatedRefs.map((article, index) => (
                <Card key={index} className="p-4 transition-colors">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="text-sm mb-1">
                        {(article as any).law_name || selectedReference.documentName}
                      </h4>
                      <p className="text-xs text-gray-500">
                        제{String((article as any).article || "")}조
                        {(article as any).paragraph ? ` 제${String((article as any).paragraph)}항` : ""}
                        {(article as any).item ? ` 제${String((article as any).item)}호` : ""}
                      </p>
                    </div>
                    <Badge variant="secondary" className="text-xs">
                      {(article as any).type}
                    </Badge>
                  </div>
                </Card>
              ))}
            </div>
          </ScrollArea>
        </TabsContent>
      </Tabs>
    </div>
  );
}
