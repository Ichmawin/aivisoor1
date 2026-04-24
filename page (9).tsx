"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { projectsApi } from "@/lib/api";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import toast from "react-hot-toast";
import { cn, formatRelative } from "@/lib/utils";
import { Plus, FolderOpen, FileText, Trash2, Edit2, Loader2, X, Check } from "lucide-react";

const schema = z.object({
  name: z.string().min(2, "At least 2 characters"),
  domain: z.string().optional(),
  niche: z.string().optional(),
  description: z.string().optional(),
});

type Form = z.infer<typeof schema>;

export default function ProjectsPage() {
  const [showCreate, setShowCreate] = useState(false);
  const qc = useQueryClient();

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => projectsApi.list().then((r) => r.data),
  });

  const { register, handleSubmit, reset, formState: { errors } } = useForm<Form>({
    resolver: zodResolver(schema),
  });

  const createMutation = useMutation({
    mutationFn: (data: Form) => projectsApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      toast.success("Project created");
      setShowCreate(false);
      reset();
    },
    onError: () => toast.error("Failed to create project"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => projectsApi.delete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["projects"] }); toast.success("Project deleted"); },
  });

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Projects</h1>
          <p className="text-gray-400 mt-1">Organize your domains and reports</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" />
          New Project
        </button>
      </div>

      {/* Create form (inline) */}
      {showCreate && (
        <div className="card mb-6 border-violet-600/40">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white">New Project</h2>
            <button onClick={() => { setShowCreate(false); reset(); }} className="text-gray-400 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          </div>
          <form onSubmit={handleSubmit(d => createMutation.mutate(d))}>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="label">Name *</label>
                <input {...register("name")} className="input" placeholder="My Brand Project" />
                {errors.name && <p className="text-red-400 text-xs mt-1">{errors.name.message}</p>}
              </div>
              <div>
                <label className="label">Domain</label>
                <input {...register("domain")} className="input" placeholder="yourbrand.com" />
              </div>
              <div className="sm:col-span-2">
                <label className="label">Industry / Niche</label>
                <input {...register("niche")} className="input" placeholder="e.g. B2B SaaS productivity tools" />
              </div>
            </div>
            <div className="flex gap-3">
              <button type="button" onClick={() => { setShowCreate(false); reset(); }} className="btn-secondary">Cancel</button>
              <button type="submit" disabled={createMutation.isPending} className="btn-primary flex items-center gap-2">
                {createMutation.isPending ? <><Loader2 className="w-4 h-4 animate-spin" />Creating…</> : <><Check className="w-4 h-4" />Create Project</>}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Projects grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-violet-400 animate-spin" />
        </div>
      ) : projects.length === 0 && !showCreate ? (
        <div className="card flex flex-col items-center justify-center py-16 text-center">
          <FolderOpen className="w-12 h-12 text-gray-700 mb-3" />
          <p className="text-white font-medium mb-1">No projects yet</p>
          <p className="text-gray-500 text-sm mb-4">Create a project to organize your domains and reports</p>
          <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
            <Plus className="w-4 h-4" />
            Create Project
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project) => (
            <div key={project.id} className="card group hover:border-gray-700 transition-colors flex flex-col">
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 bg-violet-600/20 rounded-lg flex items-center justify-center shrink-0">
                  <FolderOpen className="w-5 h-5 text-violet-400" />
                </div>
                <button
                  onClick={() => deleteMutation.mutate(project.id)}
                  disabled={deleteMutation.isPending}
                  className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400 transition-all"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              <h3 className="font-semibold text-white mb-1">{project.name}</h3>
              {project.domain && <p className="text-violet-400 text-sm mb-1">{project.domain}</p>}
              {project.niche && <p className="text-gray-400 text-xs mb-3 flex-1">{project.niche}</p>}
              <div className="flex items-center justify-between mt-auto pt-3 border-t border-gray-800">
                <div className="flex items-center gap-1 text-gray-400 text-xs">
                  <FileText className="w-3.5 h-3.5" />
                  <span>{project.report_count} report{project.report_count !== 1 ? "s" : ""}</span>
                </div>
                <span className="text-gray-600 text-xs">{formatRelative(project.created_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
