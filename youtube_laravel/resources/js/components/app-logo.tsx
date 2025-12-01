export default function AppLogo() {
    return (
        <>
            <div className="flex aspect-square size-8 items-center justify-center rounded-md bg-red-600 text-white">
                <span className="text-lg font-bold">R</span>
            </div>
            <div className="ml-1 grid flex-1 text-left text-sm">
                <span className="mb-0.5 truncate leading-tight font-semibold">
                    RedNote Manager
                </span>
            </div>
        </>
    );
}
