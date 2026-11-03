/**
 * Declares the esm.sh worker modules, which are imported with the `?worker`
 * query. Their default export starts the module in a new worker.
 */
declare module "https://esm.sh/*" {
	const createWorker: () => Worker;
	export default createWorker;
}
