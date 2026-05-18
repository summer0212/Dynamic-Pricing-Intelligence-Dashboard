"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  getRecommendations,
  generateRecommendations,
  reviewRecommendation,
} from "@/lib/api";

interface Recommendation {
  id: string;
  product_id: string;
  product_name: string;
  product_sku: string;
  recommended_price: number;
  current_price: number;
  price_change_pct: number;
  confidence_score: number;
  status: string;
  rationale: string | null;
  agent_outputs: Record<string, any> | null;
  reviewed_by: string | null;
  review_note: string | null;
  created_at: string;
}

const STATUS_TABS = ["all", "pending", "approved", "rejected"] as const;

export default function RecommendationsPage() {
  const router = useRouter();
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [orgName, setOrgName] = useState("");
  const [role, setRole] = useState("");
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [activeTab, setActiveTab] = useState<string>("all");

  // Review modal state
  const [selectedRec, setSelectedRec] = useState<Recommendation | null>(null);
  const [reviewNote, setReviewNote] = useState("");
  const [reviewing, setReviewing] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }
    setOrgName(localStorage.getItem("org_name") || "");
    setRole(localStorage.getItem("role") || "");
    fetchRecommendations();
  }, []);

  const fetchRecommendations = async (status?: string) => {
    setLoading(true);
    try {
      const filter = status && status !== "all" ? status : undefined;
      const data = await getRecommendations(filter);
      setRecommendations(data);
    } catch {
      router.push("/login");
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    fetchRecommendations(tab);
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await generateRecommendations();
      await fetchRecommendations(activeTab);
    } catch (err: any) {
      alert(err.message || "Failed to generate predictions");
    } finally {
      setGenerating(false);
    }
  };

  const handleReview = async (status: "approved" | "rejected") => {
    if (!selectedRec) return;
    setReviewing(true);
    try {
      await reviewRecommendation(selectedRec.id, {
        status,
        review_note: reviewNote || undefined,
      });
      setSelectedRec(null);
      setReviewNote("");
      await fetchRecommendations(activeTab);
    } catch (err: any) {
      alert(err.message || "Failed to review recommendation");
    } finally {
      setReviewing(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      pending: "bg-amber-900/50 text-amber-300 border-amber-700/50",
      approved: "bg-emerald-900/50 text-emerald-300 border-emerald-700/50",
      rejected: "bg-red-900/50 text-red-300 border-red-700/50",
      auto_executed: "bg-blue-900/50 text-blue-300 border-blue-700/50",
    };
    return (
      <span
        className={`px-2.5 py-1 rounded-full text-xs font-medium border ${
          styles[status] || "bg-gray-800 text-gray-400"
        }`}
      >
        {status.replace("_", " ")}
      </span>
    );
  };

  const getChangeIndicator = (pct: number) => {
    if (pct > 0)
      return <span className="text-emerald-400 font-medium">▲ +{pct.toFixed(1)}%</span>;
    if (pct < 0)
      return <span className="text-red-400 font-medium">▼ {pct.toFixed(1)}%</span>;
    return <span className="text-gray-400">—</span>;
  };

  const getConfidenceBar = (score: number) => {
    const pct = score * 100;
    let color = "bg-red-500";
    if (pct >= 80) color = "bg-emerald-500";
    else if (pct >= 65) color = "bg-amber-500";
    return (
      <div className="flex items-center gap-2">
        <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full ${color}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="text-xs text-gray-400">{pct.toFixed(0)}%</span>
      </div>
    );
  };

  if (loading)
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center text-white">
        Loading...
      </div>
    );

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4 flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold">Pricing Intelligence</h1>
          <p className="text-gray-400 text-sm">
            {orgName} • {role}
          </p>
        </div>
        <nav className="flex gap-4">
          <a href="/dashboard" className="text-gray-400 hover:text-white">
            Dashboard
          </a>
          <a href="/recommendations" className="text-blue-400">
            Recommendations
          </a>
          <button
            onClick={() => {
              localStorage.clear();
              router.push("/login");
            }}
            className="text-red-400 hover:text-red-300"
          >
            Logout
          </button>
        </nav>
      </header>

      <main className="p-6">
        {/* Title bar */}
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold">Price Recommendations</h2>
          {role === "admin" && (
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition disabled:opacity-50 flex items-center gap-2"
            >
              {generating ? (
                <>
                  <svg
                    className="animate-spin h-4 w-4"
                    viewBox="0 0 24 24"
                    fill="none"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                  Generating...
                </>
              ) : (
                "⚡ Generate Predictions"
              )}
            </button>
          )}
        </div>

        {/* Filter tabs */}
        <div className="flex gap-1 mb-6 bg-gray-900 p-1 rounded-lg w-fit">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => handleTabChange(tab)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition capitalize ${
                activeTab === tab
                  ? "bg-gray-700 text-white"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Recommendations table */}
        {recommendations.length === 0 ? (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center">
            <p className="text-gray-400 text-lg">No recommendations found.</p>
            {role === "admin" && (
              <p className="text-gray-500 mt-2">
                Click &quot;Generate Predictions&quot; to create pricing
                recommendations.
              </p>
            )}
          </div>
        ) : (
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-800">
                <tr>
                  <th className="text-left px-6 py-3 text-gray-400 text-sm">
                    Product
                  </th>
                  <th className="text-right px-6 py-3 text-gray-400 text-sm">
                    Current
                  </th>
                  <th className="text-right px-6 py-3 text-gray-400 text-sm">
                    Recommended
                  </th>
                  <th className="text-center px-6 py-3 text-gray-400 text-sm">
                    Change
                  </th>
                  <th className="text-center px-6 py-3 text-gray-400 text-sm">
                    Confidence
                  </th>
                  <th className="text-center px-6 py-3 text-gray-400 text-sm">
                    Status
                  </th>
                  <th className="text-center px-6 py-3 text-gray-400 text-sm">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody>
                {recommendations.map((rec) => (
                  <tr
                    key={rec.id}
                    className="border-t border-gray-800 hover:bg-gray-800/50"
                  >
                    <td className="px-6 py-4">
                      <div className="font-medium">{rec.product_name}</div>
                      <div className="text-xs text-gray-500">
                        {rec.product_sku}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      ₹{rec.current_price.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-right font-medium">
                      ₹{rec.recommended_price.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-center">
                      {getChangeIndicator(rec.price_change_pct)}
                    </td>
                    <td className="px-6 py-4">
                      {getConfidenceBar(rec.confidence_score)}
                    </td>
                    <td className="px-6 py-4 text-center">
                      {getStatusBadge(rec.status)}
                    </td>
                    <td className="px-6 py-4 text-center">
                      {rec.status === "pending" && role === "admin" ? (
                        <button
                          onClick={() => {
                            setSelectedRec(rec);
                            setReviewNote("");
                          }}
                          className="px-3 py-1.5 bg-blue-600/20 text-blue-400 border border-blue-700/50 rounded-lg text-sm hover:bg-blue-600/30 transition"
                        >
                          Review
                        </button>
                      ) : rec.status !== "pending" ? (
                        <button
                          onClick={() => setSelectedRec(rec)}
                          className="text-gray-500 hover:text-gray-300 text-sm"
                        >
                          Details
                        </button>
                      ) : (
                        <span className="text-gray-600 text-sm">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>

      {/* Review / Detail Modal */}
      {selectedRec && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            {/* Modal header */}
            <div className="border-b border-gray-800 px-6 py-4 flex justify-between items-center">
              <h3 className="text-lg font-bold">
                {selectedRec.status === "pending"
                  ? "Review Recommendation"
                  : "Recommendation Details"}
              </h3>
              <button
                onClick={() => setSelectedRec(null)}
                className="text-gray-500 hover:text-white text-xl"
              >
                ✕
              </button>
            </div>

            <div className="px-6 py-5 space-y-5">
              {/* Product info */}
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">
                  Product
                </p>
                <p className="font-semibold text-lg">
                  {selectedRec.product_name}
                </p>
                <p className="text-gray-400 text-sm">
                  {selectedRec.product_sku}
                </p>
              </div>

              {/* Price comparison */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-800 rounded-xl p-4">
                  <p className="text-xs text-gray-500 mb-1">Current Price</p>
                  <p className="text-2xl font-bold">
                    ₹{selectedRec.current_price.toLocaleString()}
                  </p>
                </div>
                <div className="bg-gray-800 rounded-xl p-4 border border-blue-800/50">
                  <p className="text-xs text-blue-400 mb-1">Recommended</p>
                  <p className="text-2xl font-bold text-blue-300">
                    ₹{selectedRec.recommended_price.toLocaleString()}
                  </p>
                  <p className="text-sm mt-1">
                    {getChangeIndicator(selectedRec.price_change_pct)}
                  </p>
                </div>
              </div>

              {/* Confidence */}
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">
                  Confidence Score
                </p>
                <div className="flex items-center gap-3">
                  <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        selectedRec.confidence_score >= 0.8
                          ? "bg-emerald-500"
                          : selectedRec.confidence_score >= 0.65
                          ? "bg-amber-500"
                          : "bg-red-500"
                      }`}
                      style={{
                        width: `${selectedRec.confidence_score * 100}%`,
                      }}
                    />
                  </div>
                  <span className="text-sm font-medium">
                    {(selectedRec.confidence_score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              {/* Rationale */}
              {selectedRec.rationale && (
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">
                    AI Rationale
                  </p>
                  <p className="text-sm text-gray-300 bg-gray-800 rounded-lg p-3 leading-relaxed">
                    {selectedRec.rationale}
                  </p>
                </div>
              )}

              {/* Agent outputs */}
              {selectedRec.agent_outputs && (
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">
                    Agent Analysis
                  </p>
                  <div className="bg-gray-800 rounded-lg p-3 text-xs font-mono text-gray-400 overflow-x-auto">
                    <pre>
                      {JSON.stringify(selectedRec.agent_outputs, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

              {/* Review note (for already-reviewed) */}
              {selectedRec.review_note &&
                selectedRec.status !== "pending" && (
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">
                      Review Note
                    </p>
                    <p className="text-sm text-gray-300">
                      {selectedRec.review_note}
                    </p>
                  </div>
                )}

              {/* Review actions (only for pending + admin) */}
              {selectedRec.status === "pending" && role === "admin" && (
                <>
                  <div>
                    <label className="text-xs text-gray-500 uppercase tracking-wider block mb-2">
                      Review Note (optional)
                    </label>
                    <textarea
                      value={reviewNote}
                      onChange={(e) => setReviewNote(e.target.value)}
                      placeholder="Add a note about this decision..."
                      className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 resize-none"
                      rows={3}
                    />
                  </div>

                  <div className="flex gap-3">
                    <button
                      onClick={() => handleReview("approved")}
                      disabled={reviewing}
                      className="flex-1 py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-lg transition disabled:opacity-50"
                    >
                      {reviewing ? "Processing..." : "✓ Approve & Apply Price"}
                    </button>
                    <button
                      onClick={() => handleReview("rejected")}
                      disabled={reviewing}
                      className="flex-1 py-3 bg-red-600/20 hover:bg-red-600/30 text-red-400 border border-red-700/50 font-semibold rounded-lg transition disabled:opacity-50"
                    >
                      {reviewing ? "Processing..." : "✗ Reject"}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
