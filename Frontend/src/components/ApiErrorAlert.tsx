import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";

export function ApiErrorAlert({ error, onRetry }: { error?: unknown; onRetry?: () => void }) {
  if (!error) return null;
  const status = error instanceof ApiError ? error.status : undefined;
  const message = friendlyMessage(error);
  return (
    <div className="rounded-xl border border-[#e7bdb4] bg-[#fff2ee] p-4 text-sm text-[#7c3529]" role="alert">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="font-extrabold">{status ? `We couldn’t complete that (${status})` : "We couldn’t complete that"}</p>
          <p className="mt-1 break-words">{message}</p>
          {onRetry ? (
            <Button className="mt-3" variant="secondary" type="button" onClick={onRetry}>
              Retry
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function friendlyMessage(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 400) return "Please check the details and try again.";
    if (error.status === 401) return "Your session has expired. Please log in again.";
    if (error.status === 404) return "We could not find that saved item yet.";
    if (error.status === 409) return "Please choose whether to use your saved preferences.";
    if (error.status === 422) {
      const detail = error.detail;
      if (Array.isArray(detail) && detail.length > 0) {
        return detail.map((d: { msg?: string }) => d.msg ?? "Invalid value").join("; ");
      }
      return "Invalid input data. Please check your form values and try again.";
    }
    if (error.status === 500 || error.status === 502) return "The planner service had trouble completing this step. Please retry.";
    return "Something went wrong while contacting the planner service.";
  }

  if (error instanceof Error) return error.message;
  return "Something went wrong. Please retry.";
}
