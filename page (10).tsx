"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { reportsApi } from "@/lib/api";
import { ScoreRing, NewReportModal } from "@/components/dashboard/ScoreRing";
import { cn, formatRelative, scoreColor } from "@/lib/utils";
import {
  Plus, Search, Loader2, AlertCircle, Clock,
  CheckCircle2, FileText, Trash2, ExternalLink,
} from "lucide-react";
import Link from "next/link";
import toast from "react-hot-toast";

const STATUS_CONFIG = {
  pending: { icon: Clock, color: "text-gray-400", label: "Pending" },
  running: { icon: Loader2, color: "text-blue-400", label: "Running", spin: true },
  done: { icon: CheckCircle2, color: "text-emerald-400", label: "Done" },
  failed: { icon: AlertCircle, color: "text-red-400", label: "Failed" },
} as const;

export default function ReportsPage() {
  const [showModal, setShowModal] = useState(false);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const qc = useQueryClient();

  const { data: reports = [], isLoading } = useQuery({
    queryKey: ["reports"],
    queryFn: () => reportsApi.list(1, 50).then((r) => r.data),
    refetchInterval: (data) =>
      (data ?? []).some((r) => r.status === "pending" || r.status === "running") ? 5000 : false,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => reportsApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["reports"] });
      toast.success("Report deleted");
    },
  });

  const filtered = reports.filter((r) => {
    const matchSearch = r.domain.toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === "all" || r.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const stats = {
    total: reports.length,
    done: reports.filter((r) => r.status === "done").length,
    avgScore: reports.filter((r) => r.score_overall).length
      ? Math.round(reports.filter((r) => r.score_overall).reduce((s, r) => s + (r.score_overall ?? 0), 0) / reports.filter((r) => r.score_overall).length)
      : null,
  };

  return (
    <div className="p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Reports</h1>
          <p className="text-gray-400 mt-1">
            {stats.total} total · {stats.done} completed
            {stats.avgScore !== null && ` · Avg score: ${stats.avgScore}`}
          </p>
        </div>
        <button onClick={() => setShowModal(true)} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" />
          New Report
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <div className="relative flex-1 min-w-48 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search domains…"
            className="input pl-9"
          />
        </div>
        <div className="flex gap-1 bg-gray-900 border border-gray-800 rounded-lg p-1">
          {["all", "done", "running", "pending", "failed"].map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={cn(
                "px-3 py-1.5 rounded-md text-xs font-medium capitalize transition-colors",
                statusFilter === s ? "bg-gray-700 text-white" : "text-gray-400 hover:text-white"
              )}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-violet-400 animate-spin" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="card flex flex-col items-center justify-center py-16 text-center">
          <FileText className="w-12 h-12 text-gray-700 mb-3" />
          <p className="text-white font-medium mb-1">
            {search || statusFilter !== "all" ? "No reports match your filters" : "No reports yet"}
          </p>
          <p className="text-gray-500 text-sm mb-4">
            {search || statusFilter !== "all"
              ? "Try adjusting your filters"
              : "Run your first AI visibility analysis"}
          </p>
          {!search && statusFilter === "all" && (
            <button onClick={() => setShowModal(true)} className="btn-primary flex items-center gap-2">
              <Plus className="w-4 h-4" />
              Create Report
            </button>
          )}
        </div>
      ) : (
        <div className="card overflow-hidden p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800">
                {["Domain", "Score", "Status", "Date", ""].map((h) => (
                  <th key={h} className="text-left text-gray-400 font-medium py-3 px-4">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {filtered.map((report) => {
                const StatusIcon = STATUS_CONFIG[report.status].icon;
                const spin = (STATUS_CONFIG[report.status] as any).spin;
                return (
                  <tr key={report.id} className="hover:bg-gray-800/40 transition-colors group">
                    <td className="py-3 px-4">
                      <p className="font-medium text-white">{report.domain}</p>
                      {report.niche && (
                        <p className="text-xs text-gray-500 mt-0.5">{report.niche}</p>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      {report.score_overall !== null ? (
                        <span className={cn("text-lg font-bold", scoreColor(report.score_overall))}>
                          {report.score_overall}
                          <span className="text-gray-600 text-xs font-normal">/100</span>
                        </span>
                      ) : (
                        <span className="text-gray-600">—</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5">
                        <StatusIcon
                          className={cn("w-4 h-4", STATUS_CONFIG[report.status].color, spin && "animate-spin")}
                        />
                        <span className={cn("text-xs", STATUS_CONFIG[report.status].color)}>
                          {STATUS_CONFIG[report.status].label}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-gray-400 text-xs whitespace-nowrap">
                      {formatRelative(report.created_at)}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        {report.status === "done" && (
                          <Link href={`/dashboard/reports/${report.id}`}
                            className="text-violet-400 hover:text-violet-300">
                            <ExternalLink className="w-4 h-4" />
                          </Link>
                        )}
                        <button
                          onClick={() => deleteMutation.mutate(report.id)}
                          disabled={deleteMutation.isPending}
                          className="text-gray-500 hover:text-red-400 transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {showModal && <NewReportModal onClose={() => setShowModal(false)} />}
    </div>
  );
}
