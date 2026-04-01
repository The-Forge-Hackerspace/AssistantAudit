import { Progress } from "@/components/ui/progress";
import type { ChecklistProgress } from "@/types";

interface ChecklistProgressProps {
  progress: ChecklistProgress;
}

export function ChecklistProgressBar({ progress }: ChecklistProgressProps) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">
          {progress.answered} / {progress.total_items} vérifiés
        </span>
        <span className="font-semibold">{progress.progress_percent}%</span>
      </div>
      <Progress value={progress.progress_percent} className="h-3" />
      <div className="flex gap-4 text-xs text-muted-foreground">
        <span className="text-green-600 font-medium">{progress.ok} OK</span>
        <span className="text-red-600 font-medium">{progress.nok} NOK</span>
        <span className="text-gray-500 font-medium">{progress.na} N/A</span>
        <span className="text-gray-400">{progress.unchecked} non vérifiés</span>
      </div>
    </div>
  );
}
