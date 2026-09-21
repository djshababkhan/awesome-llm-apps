"use client";

import { useState, useRef, useEffect } from "react";
import { Upload, FileText, Loader2, Sparkles, FolderOpen, Bot, CheckCircle, Code, BookOpen, Layers } from "lucide-react";

interface UploadStepProps {
  onComplete: (
    sessionId: string,
    apiKey: string,
    metadata: any,
    scenarios: any[],
    evals: any[]
  ) => void;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8891";

export default function UploadStep({ onComplete }: UploadStepProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [fileList, setFileList] = useState<string[]>([]);
  const [metadata, setMetadata] = useState<any>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [availableSkills, setAvailableSkills] = useState<any[]>([]);
  const [selectedSkillPath, setSelectedSkillPath] = useState<string | null>(null);
  const [isLoadingSkills, setIsLoadingSkills] = useState(false);
  const folderInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchAvailableSkills();
  }, []);

  const fetchAvailableSkills = async () => {
    setIsLoadingSkills(true);
    try {
      const response = await fetch(`${API_BASE}/api/examples`);
      if (response.ok) {
        const data = await response.json();
        setAvailableSkills(data.examples || []);
      }
    } catch (e) {
      console.error("Failed to fetch available skills:", e);
    } finally {
      setIsLoadingSkills(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    const zipFile = files.find((f) => f.name.endsWith(".zip"));
    if (zipFile) {
      await uploadZip(zipFile);
    } else if (files.length > 0) {
      await uploadMultipleFiles(files);
    }
  };

  const handleZipSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files[0]) {
      await uploadZip(files[0]);
    }
  };

  const handleFolderSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      await uploadMultipleFiles(Array.from(files));
    }
  };

  const uploadZip = async (file: File) => {
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`${API_BASE}/api/upload`, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || "Upload failed");
      }
      const data = await response.json();
      setSessionId(data.session_id);
      setFileList(data.file_list);
      setMetadata(data.metadata);
    } catch (error: any) {
      alert(error.message || "Upload failed. Please try again.");
    } finally {
      setIsUploading(false);
    }
  };

  const uploadMultipleFiles = async (files: File[]) => {
    setIsUploading(true);
    try {
      const formData = new FormData();
      for (const f of files) {
        const path = (f as any).webkitRelativePath || f.name;
        formData.append("files", f, path);
      }
      const response = await fetch(`${API_BASE}/api/upload-files`, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || "Upload failed");
      }
      const data = await response.json();
      setSessionId(data.session_id);
      setFileList(data.file_list);
      setMetadata(data.metadata);
    } catch (error: any) {
      alert(error.message || "Upload failed. Please try again.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleAnalyze = async () => {
    if (!apiKey || !sessionId) return;
    setIsAnalyzing(true);
    try {
      const response = await fetch(`${API_BASE}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, gemini_api_key: apiKey }),
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || "Analysis failed");
      }
      const data = await response.json();
      onComplete(sessionId, apiKey, metadata, data.scenarios, data.evals);
    } catch (error: any) {
      alert(error.message || "Analysis failed. Check your API key.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleExampleSelect = async (examplePath: string) => {
    if (!apiKey) {
      alert("Please enter your Google API key first.");
      return;
    }
    setSelectedSkillPath(examplePath);
    setIsUploading(true);
    try {
      const loadResponse = await fetch(`${API_BASE}/api/examples/${examplePath}/load`, {
        method: "POST",
      });
      if (!loadResponse.ok) throw new Error("Failed to load skill");
      const loadData = await loadResponse.json();
      setSessionId(loadData.session_id);
      setFileList(loadData.file_list);
      setMetadata(loadData.metadata);
      setIsUploading(false);
      setIsAnalyzing(true);

      const analyzeResponse = await fetch(`${API_BASE}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: loadData.session_id, gemini_api_key: apiKey }),
      });
      if (!analyzeResponse.ok) {
        const err = await analyzeResponse.json().catch(() => ({}));
        throw new Error(err.detail || "Analysis failed");
      }
      const analyzeData = await analyzeResponse.json();
      onComplete(loadData.session_id, apiKey, loadData.metadata, analyzeData.scenarios, analyzeData.evals);
    } catch (error: any) {
      alert(error.message || "Failed to load skill.");
      setSessionId(null);
    } finally {
      setIsUploading(false);
      setIsAnalyzing(false);
      setSelectedSkillPath(null);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {!sessionId ? (
        <>
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`glass rounded-2xl p-16 text-center transition-all ${
              isDragging ? "border-violet-500 bg-violet-500/10 scale-105" : "border-zinc-800 hover:border-zinc-700"
            }`}
          >
            <input type="file" accept=".zip" onChange={handleZipSelect} className="hidden" id="zip-upload" />
            <input
              type="file"
              ref={folderInputRef}
              onChange={handleFolderSelect}
              className="hidden"
              id="folder-upload"
              {...({ webkitdirectory: "", directory: "" } as any)}
              multiple
            />

            <div className="mb-6">
              {isUploading ? (
                <Loader2 className="w-16 h-16 mx-auto text-violet-500 animate-spin" />
              ) : (
                <Upload className="w-16 h-16 mx-auto text-zinc-500" />
              )}
            </div>

            <h3 className="text-2xl font-semibold mb-2">
              {isUploading ? "Uploading..." : "Drop your skill here"}
            </h3>
            <p className="text-zinc-400 mb-4">Drag a .zip file or use the buttons below</p>

            <div className="flex justify-center gap-4">
              <label
                htmlFor="zip-upload"
                className="px-6 py-3 bg-zinc-800 hover:bg-zinc-700 rounded-xl cursor-pointer transition-colors flex items-center gap-2 text-sm font-medium"
              >
                <Upload className="w-4 h-4" />
                Upload .zip
              </label>
              <button
                onClick={() => folderInputRef.current?.click()}
                className="px-6 py-3 bg-zinc-800 hover:bg-zinc-700 rounded-xl cursor-pointer transition-colors flex items-center gap-2 text-sm font-medium"
              >
                <FolderOpen className="w-4 h-4" />
                Upload Folder
              </button>
            </div>
          </div>

          <div className="glass rounded-2xl p-6">
            <label className="block">
              <span className="text-sm font-medium text-zinc-400 mb-2 block">Google API Key</span>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Enter your Google API key"
                className="w-full px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg focus:outline-none focus:border-violet-500 transition-colors"
              />
              <span className="text-xs text-zinc-500 mt-1 block">
                Required for analysis. Stored locally, sent only to the backend.
              </span>
            </label>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-bold flex items-center gap-2">
                <Bot className="w-5 h-5 text-violet-500" />
                Repository Agent Skills Dashboard
              </h3>
              <span className="text-xs px-3 py-1 bg-violet-500/10 text-violet-400 rounded-full border border-violet-500/20 font-medium">
                {availableSkills.length} Skills Detected
              </span>
            </div>

            <p className="text-sm text-zinc-400">
              Select any agent skill below to inspect, generate scenarios, and run self-improvement optimization:
            </p>

            {isLoadingSkills ? (
              <div className="text-center py-8 glass rounded-xl">
                <Loader2 className="w-8 h-8 animate-spin mx-auto text-violet-500 mb-2" />
                <p className="text-sm text-zinc-400">Loading skills dashboard...</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {availableSkills.map((skill) => {
                  const isSelectedLoading = selectedSkillPath === skill.path && (isUploading || isAnalyzing);
                  return (
                    <div
                      key={skill.path}
                      className={`glass rounded-xl p-5 border text-left transition-all flex flex-col justify-between ${
                        selectedSkillPath === skill.path
                          ? "border-violet-500 bg-violet-500/5"
                          : "border-zinc-800 hover:border-zinc-700"
                      }`}
                    >
                      <div>
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <h4 className="font-bold text-base flex items-center gap-2 text-zinc-100">
                            {skill.name}
                          </h4>
                          <span className="text-xs px-2 py-0.5 bg-zinc-800 text-zinc-400 rounded font-mono">
                            {skill.file_count} files
                          </span>
                        </div>
                        <p className="text-xs text-zinc-400 line-clamp-3 mb-4 leading-relaxed">
                          {skill.description || "No description provided."}
                        </p>
                      </div>

                      <div>
                        <div className="flex items-center gap-2 mb-4 text-[11px] text-zinc-400">
                          {skill.has_evals && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded border border-emerald-500/20">
                              <CheckCircle className="w-3 h-3" /> Evals
                            </span>
                          )}
                          {skill.has_scripts && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-500/10 text-blue-400 rounded border border-blue-500/20">
                              <Code className="w-3 h-3" /> Scripts
                            </span>
                          )}
                          {skill.has_references && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-violet-500/10 text-violet-400 rounded border border-violet-500/20">
                              <BookOpen className="w-3 h-3" /> Refs
                            </span>
                          )}
                        </div>

                        <button
                          onClick={() => handleExampleSelect(skill.path)}
                          disabled={isUploading || isAnalyzing || !apiKey}
                          className={`w-full py-2.5 px-4 rounded-lg text-xs font-semibold transition-all flex items-center justify-center gap-2 ${
                            apiKey && !isUploading && !isAnalyzing
                              ? "bg-violet-600 hover:bg-violet-500 text-white shadow-lg shadow-violet-600/20 cursor-pointer"
                              : "bg-zinc-800 text-zinc-500 cursor-not-allowed"
                          }`}
                        >
                          {isSelectedLoading ? (
                            <>
                              <Loader2 className="w-4 h-4 animate-spin text-white" />
                              Analyzing Skill...
                            </>
                          ) : (
                            <>
                              <Sparkles className="w-4 h-4" />
                              Select & Optimize Skill
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </>
      ) : (
        <div className="space-y-6">
          <div className="glass rounded-2xl p-8">
            <div className="flex items-start gap-4 mb-6">
              <FileText className="w-8 h-8 text-violet-500" />
              <div className="flex-1">
                <h3 className="text-xl font-semibold mb-1">{metadata?.name || "Skill Uploaded"}</h3>
                {metadata?.description && <p className="text-zinc-400">{metadata.description}</p>}
              </div>
            </div>
            <div className="border-t border-zinc-800 pt-4 mt-4">
              <p className="text-sm text-zinc-500 mb-2">Files in skill:</p>
              <div className="flex flex-wrap gap-2">
                {fileList.map((file) => (
                  <span key={file} className="px-3 py-1 bg-zinc-800 rounded-full text-xs text-zinc-300">
                    {file}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div className="glass rounded-2xl p-8">
            <label className="block mb-4">
              <span className="text-sm font-medium text-zinc-400 mb-2 block">Google API Key</span>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Enter your Google API key"
                className="w-full px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg focus:outline-none focus:border-violet-500 transition-colors"
              />
            </label>
            <button
              onClick={handleAnalyze}
              disabled={!apiKey || isAnalyzing}
              className={`w-full py-4 rounded-xl font-semibold transition-all flex items-center justify-center gap-2 ${
                apiKey && !isAnalyzing ? "gradient-bg hover:scale-105" : "bg-zinc-800 text-zinc-500 cursor-not-allowed"
              }`}
            >
              {isAnalyzing ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Analyzing Skill...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  Analyze Skill
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
