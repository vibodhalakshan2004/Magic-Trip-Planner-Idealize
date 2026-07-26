import { PlannerWorkspace } from "@/components/planner/PlannerWorkspace";

export default async function ExistingPlannerPage({ params }: { params: Promise<{ tripId: string }> }) {
  const { tripId } = await params;
  return <PlannerWorkspace tripId={tripId} />;
}
