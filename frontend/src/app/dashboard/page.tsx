"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getProducts, getRecommendations } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [products, setProducts] = useState<any[]>([]);
  const [orgName, setOrgName] = useState("");
  const [role, setRole] = useState("");
  const [loading, setLoading] = useState(true);
  const [pendingCount, setPendingCount] = useState(0);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }
    setOrgName(localStorage.getItem("org_name") || "");
    setRole(localStorage.getItem("role") || "");

    Promise.all([
      getProducts(),
      getRecommendations("pending").catch(() => []),
    ])
      .then(([productData, pendingRecs]) => {
        setProducts(productData);
        setPendingCount(pendingRecs.length);
      })
      .catch(() => router.push("/login"))
      .finally(() => setLoading(false));
  }, []);

  const totalProducts = products.length;
  const totalValue = products.reduce((sum, p) => sum + p.current_price * p.inventory_count, 0);
  const lowStock = products.filter((p) => p.inventory_count < 50).length;
  const categories = [...new Set(products.map((p) => p.category))].length;

  if (loading) return <div className="min-h-screen bg-gray-950 flex items-center justify-center text-white">Loading...</div>;

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4 flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold">Pricing Intelligence</h1>
          <p className="text-gray-400 text-sm">{orgName} • {role}</p>
        </div>
        <nav className="flex gap-4">
          <a href="/dashboard" className="text-blue-400">Dashboard</a>
          <a href="/recommendations" className="text-gray-400 hover:text-white">Recommendations</a>
          <button onClick={() => { localStorage.clear(); router.push("/login"); }}
            className="text-red-400 hover:text-red-300">Logout</button>
        </nav>
      </header>

      {/* Summary Cards */}
      <main className="p-6">
        <h2 className="text-2xl font-bold mb-6">Dashboard</h2>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <p className="text-gray-400 text-sm">Total Products</p>
            <p className="text-3xl font-bold mt-1">{totalProducts}</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <p className="text-gray-400 text-sm">Inventory Value</p>
            <p className="text-3xl font-bold mt-1">₹{totalValue.toLocaleString()}</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <p className="text-gray-400 text-sm">Low Stock Items</p>
            <p className="text-3xl font-bold mt-1 text-yellow-400">{lowStock}</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <p className="text-gray-400 text-sm">Categories</p>
            <p className="text-3xl font-bold mt-1">{categories}</p>
          </div>
          <a href="/recommendations" className="bg-gray-900 border border-gray-800 rounded-xl p-6 hover:border-amber-700/50 transition group">
            <p className="text-gray-400 text-sm group-hover:text-amber-400 transition">Pending Recommendations</p>
            <p className="text-3xl font-bold mt-1 text-amber-400">{pendingCount}</p>
            <p className="text-xs text-gray-600 mt-1 group-hover:text-gray-400 transition">Click to review →</p>
          </a>
        </div>

        {/* Recent Products */}
        <h3 className="text-xl font-semibold mb-4">Recent Products</h3>
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-800">
              <tr>
                <th className="text-left px-6 py-3 text-gray-400 text-sm">Product</th>
                <th className="text-left px-6 py-3 text-gray-400 text-sm">SKU</th>
                <th className="text-left px-6 py-3 text-gray-400 text-sm">Category</th>
                <th className="text-right px-6 py-3 text-gray-400 text-sm">Price</th>
                <th className="text-right px-6 py-3 text-gray-400 text-sm">Stock</th>
              </tr>
            </thead>
            <tbody>
              {products.slice(0, 5).map((p) => (
                <tr key={p.id} className="border-t border-gray-800 hover:bg-gray-800/50">
                  <td className="px-6 py-4">{p.name}</td>
                  <td className="px-6 py-4 text-gray-400">{p.sku}</td>
                  <td className="px-6 py-4">
                    <span className="px-2 py-1 bg-blue-900/50 text-blue-300 rounded text-xs">
                      {p.category}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">₹{p.current_price.toLocaleString()}</td>
                  <td className="px-6 py-4 text-right">{p.inventory_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
