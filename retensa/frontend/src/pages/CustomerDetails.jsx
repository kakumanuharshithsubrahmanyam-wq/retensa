import { useParams } from "react-router-dom";
import { useCustomerAnalysis } from "../hooks/useCustomer";
import ActionCenterView from "../components/ActionCenterView";
import StatusBox from "../components/ui";

export default function CustomerDetails() {
  const { customerIndex } = useParams();
  const { data, loading, error } = useCustomerAnalysis(customerIndex);

  return (
    <main className="page">
      <StatusBox loading={loading} error={error} loadingText="Loading customer analysis…">
        {data && (
          <ActionCenterView
            data={data}
            title={`Customer #${customerIndex}`}
            askAiTo={`/assistant?customer=${customerIndex}`}
          />
        )}
      </StatusBox>
    </main>
  );
}
