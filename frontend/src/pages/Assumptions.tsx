import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api } from "../lib/api";
import { useApi } from "../lib/useApi";
import { Card, Loading, ErrorState } from "../components/ui";

export default function Assumptions() {
  const { data, error, loading } = useApi(api.assumptions);
  if (loading) return <Loading />;
  if (error || !data) return <ErrorState message={error ?? "no data"} />;

  return (
    <Card>
      <div className="assumptions max-w-none">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{data.markdown}</ReactMarkdown>
      </div>
    </Card>
  );
}
