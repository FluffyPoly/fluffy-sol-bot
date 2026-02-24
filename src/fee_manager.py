"""
Fee Manager - Auto USDC→SOL swaps for trading fees
Never get stuck without SOL for gas!
"""
import json
from datetime import datetime
from typing import Optional
import asyncio

class FeeManager:
    def __init__(self, wallet_manager, jupiter_client):
        self.wallet_manager = wallet_manager
        self.jupiter_client = jupiter_client
        self.reserve_target = 0.5  # SOL (≈$75)
        self.swap_threshold = 0.1  # SOL (≈$15) - trigger swap below this
        self.swap_amount_usdc = 5.0  # USDC to swap each time
        self.log_path = 'data/fee_swaps.jsonl'
        
    async def check_and_refill(self):
        """Check SOL balance, auto-swap if low"""
        sol_balance = await self.wallet_manager.get_sol_balance()
        
        if sol_balance < self.swap_threshold:
            print(f"⚠️ SOL low: {sol_balance:.4f} SOL (< {self.swap_threshold})")
            print(f"🔄 Swapping {self.swap_amount_usdc} USDC → SOL...")
            
            success = await self._swap_usdc_to_sol(self.swap_amount_usdc)
            
            if success:
                self._log_swap(sol_balance, self.swap_amount_usdc)
                print(f"✅ Fee reserve refilled!")
            else:
                print(f"❌ Swap failed!")
            
            return success
        
        return True  # No action needed
    
    async def _swap_usdc_to_sol(self, amount_usdc: float) -> bool:
        """Execute USDC → SOL swap via Jupiter"""
        try:
            # Get quote
            quote = await self.jupiter_client.get_quote(
                input_mint='EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
                output_mint='So11111111111111111111111111111111111111112',  # SOL
                amount=int(amount_usdc * 1_000_000),  # USDC 6 decimals
                slippage_bps=50  # 0.5%
            )
            
            # Execute swap
            swap_tx = await self.jupiter_client.get_swap_instruction(quote)
            signature = await self.wallet_manager.sign_and_send(swap_tx)
            
            print(f"💸 Swap signature: {signature[:20]}...")
            return True
            
        except Exception as e:
            print(f"Swap error: {e}")
            return False
    
    def _log_swap(self, balance_before: float, amount_usdc: float):
        """Log swap to file"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'balance_before': balance_before,
            'amount_usdc': amount_usdc,
            'type': 'fee_reserve_refill'
        }
        
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def get_swap_history(self, limit: int = 10) -> list:
        """Get recent swap history"""
        try:
            with open(self.log_path, 'r') as f:
                lines = f.readlines()
                return [json.loads(line) for line in lines[-limit:]]
        except FileNotFoundError:
            return []
    
    def get_status(self) -> dict:
        """Get fee manager status"""
        return {
            'reserve_target': self.reserve_target,
            'swap_threshold': self.swap_threshold,
            'swap_amount_usdc': self.swap_amount_usdc,
            'recent_swaps': self.get_swap_history(5)
        }


async def test_fee_manager():
    """Test fee manager (mock)"""
    # Mock objects for testing
    class MockWallet:
        async def get_sol_balance(self):
            return 0.05  # Low balance - should trigger swap
        
        async def sign_and_send(self, tx):
            return 'mock_signature_123'
    
    class MockJupiter:
        async def get_quote(self, **kwargs):
            return {'quote': 'mock'}
        
        async def get_swap_instruction(self, quote):
            return 'mock_tx'
    
    fee_mgr = FeeManager(MockWallet(), MockJupiter())
    result = await fee_mgr.check_and_refill()
    print(f"Fee check result: {result}")
    print(f"Status: {fee_mgr.get_status()}")


if __name__ == '__main__':
    asyncio.run(test_fee_manager())
