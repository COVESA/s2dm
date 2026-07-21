import Layout from "@theme/Layout";

export default function VoyagerPage() {
  return (
    <Layout title="Schema Visualizer" noFooter>
      <iframe
        src="/voyager.html"
        style={{ width: "100%", height: "calc(100vh - 60px)", border: "none" }}
        title="GraphQL Voyager"
      />
    </Layout>
  );
}
