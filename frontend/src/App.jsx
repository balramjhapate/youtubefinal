import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Layout } from "./components/layout";
import {
	Dashboard,
	Videos,
	Settings,
	VideoDetail,
} from "./pages";

// Create a client
const queryClient = new QueryClient({
	defaultOptions: {
		queries: {
			staleTime: 1000 * 60, // 1 minute
			retry: 1,
			refetchOnWindowFocus: false,
		},
	},
});

function App() {
	return (
		<QueryClientProvider client={queryClient}>
			<BrowserRouter>
				<Layout>
					<Routes>
						<Route path="/" element={<Dashboard />} />
						<Route path="/videos" element={<Videos />} />
						<Route path="/videos/:id" element={<VideoDetail />} />
						<Route path="/settings" element={<Settings />} />
					</Routes>
				</Layout>
			</BrowserRouter>
		</QueryClientProvider>
	);
}

export default App;
