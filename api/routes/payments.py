"""
Payment API Routes

Handles Stripe and TrySpeed payment integrations.
Ready for activation when premium tools launch.
"""
import os
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel
import hmac
import hashlib

router = APIRouter(prefix="/payments", tags=["payments"])


# =============================================================================
# STRIPE INTEGRATION
# =============================================================================

class CreateCheckoutRequest(BaseModel):
    """Request to create a Stripe checkout session."""
    price_id: str
    success_url: str
    cancel_url: str
    user_id: Optional[str] = None


class CheckoutResponse(BaseModel):
    """Response with checkout session URL."""
    checkout_url: str
    session_id: str


@router.post("/stripe/checkout", response_model=CheckoutResponse)
async def create_stripe_checkout(request: CreateCheckoutRequest):
    """
    Create a Stripe Checkout session for subscription.
    
    Note: This endpoint is ready but inactive until premium tools launch.
    """
    stripe_secret = os.getenv("STRIPE_SECRET_KEY")
    if not stripe_secret:
        raise HTTPException(
            status_code=503,
            detail="Stripe payments not configured. Premium features coming soon!"
        )
    
    try:
        import stripe
        stripe.api_key = stripe_secret
        
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[
                {
                    "price": request.price_id,
                    "quantity": 1,
                },
            ],
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            metadata={
                "user_id": request.user_id,
            } if request.user_id else {},
        )
        
        return CheckoutResponse(
            checkout_url=session.url,
            session_id=session.id,
        )
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Stripe SDK not installed. Run: pip install stripe"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
):
    """
    Handle Stripe webhook events.
    
    Events handled:
    - checkout.session.completed: Activate subscription
    - customer.subscription.updated: Update subscription status
    - customer.subscription.deleted: Cancel subscription
    - invoice.payment_failed: Handle failed payment
    """
    stripe_secret = os.getenv("STRIPE_SECRET_KEY")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    if not stripe_secret or not webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    
    try:
        import stripe
        stripe.api_key = stripe_secret
        
        payload = await request.body()
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, webhook_secret
        )
        
        # Handle the event
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            user_id = session.get("metadata", {}).get("user_id")
            
            # TODO: Activate subscription in database
            print(f"Checkout completed for user: {user_id}")
            
        elif event["type"] == "customer.subscription.updated":
            subscription = event["data"]["object"]
            # TODO: Update subscription status in database
            print(f"Subscription updated: {subscription['id']}")
            
        elif event["type"] == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            # TODO: Cancel subscription in database
            print(f"Subscription cancelled: {subscription['id']}")
            
        elif event["type"] == "invoice.payment_failed":
            invoice = event["data"]["object"]
            # TODO: Handle failed payment (email user, update status)
            print(f"Payment failed for invoice: {invoice['id']}")
        
        return {"status": "success"}
        
    except ImportError:
        raise HTTPException(status_code=503, detail="Stripe SDK not installed")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/stripe/portal")
async def create_customer_portal(user_id: str):
    """
    Create a Stripe Customer Portal session for subscription management.
    """
    stripe_secret = os.getenv("STRIPE_SECRET_KEY")
    if not stripe_secret:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    
    try:
        import stripe
        stripe.api_key = stripe_secret
        
        # TODO: Get customer ID from database
        # customer_id = await get_customer_id(user_id)
        customer_id = None
        
        if not customer_id:
            raise HTTPException(status_code=404, detail="No subscription found")
        
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=os.getenv("APP_URL", "https://johnnybets.com"),
        )
        
        return {"portal_url": session.url}
        
    except ImportError:
        raise HTTPException(status_code=503, detail="Stripe SDK not installed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# TRYSPEED (STABLECOIN) INTEGRATION
# =============================================================================

class TrySpeedCheckoutRequest(BaseModel):
    """Request to create a TrySpeed checkout."""
    amount_usd: float  # Amount in USD
    currency: str = "USDC"  # USDC or USDT
    chain: str = "ethereum"  # ethereum, polygon, solana, etc.
    user_id: Optional[str] = None
    description: str = "JohnnyBets Pro Subscription"


class TrySpeedCheckoutResponse(BaseModel):
    """Response with TrySpeed payment details."""
    payment_id: str
    payment_url: str
    wallet_address: str
    amount: float
    currency: str
    chain: str
    expires_at: str


@router.post("/tryspeed/checkout", response_model=TrySpeedCheckoutResponse)
async def create_tryspeed_checkout(request: TrySpeedCheckoutRequest):
    """
    Create a TrySpeed stablecoin payment.
    
    Supports USDC and USDT on multiple chains:
    - Ethereum
    - Polygon
    - Solana
    - Arbitrum
    - Base
    
    Note: This endpoint is ready but inactive until premium tools launch.
    """
    tryspeed_api_key = os.getenv("TRYSPEED_API_KEY")
    tryspeed_secret = os.getenv("TRYSPEED_SECRET")
    
    if not tryspeed_api_key:
        raise HTTPException(
            status_code=503,
            detail="TrySpeed payments not configured. Premium features coming soon!"
        )
    
    try:
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.tryspeed.com/v1/payments",
                headers={
                    "Authorization": f"Bearer {tryspeed_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "amount": request.amount_usd,
                    "currency": request.currency,
                    "chain": request.chain,
                    "description": request.description,
                    "metadata": {
                        "user_id": request.user_id,
                        "product": "pro_subscription",
                    },
                    "webhook_url": os.getenv("APP_URL", "") + "/api/payments/tryspeed/webhook",
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"TrySpeed error: {response.text}"
                )
            
            data = response.json()
            
            return TrySpeedCheckoutResponse(
                payment_id=data["id"],
                payment_url=data["payment_url"],
                wallet_address=data["wallet_address"],
                amount=data["amount"],
                currency=data["currency"],
                chain=data["chain"],
                expires_at=data["expires_at"],
            )
            
    except ImportError:
        raise HTTPException(status_code=503, detail="httpx not installed")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tryspeed/webhook")
async def tryspeed_webhook(
    request: Request,
    x_tryspeed_signature: str = Header(None, alias="X-TrySpeed-Signature"),
):
    """
    Handle TrySpeed webhook events.
    
    Events handled:
    - payment.completed: Activate subscription
    - payment.failed: Handle failed payment
    - payment.expired: Handle expired payment
    """
    tryspeed_secret = os.getenv("TRYSPEED_SECRET")
    
    if not tryspeed_secret:
        raise HTTPException(status_code=503, detail="TrySpeed not configured")
    
    payload = await request.body()
    
    # Verify webhook signature
    expected_signature = hmac.new(
        tryspeed_secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(expected_signature, x_tryspeed_signature or ""):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    try:
        event = json.loads(payload)
        event_type = event.get("type")
        data = event.get("data", {})
        
        if event_type == "payment.completed":
            payment_id = data.get("id")
            user_id = data.get("metadata", {}).get("user_id")
            
            # TODO: Activate subscription in database
            print(f"TrySpeed payment completed: {payment_id} for user {user_id}")
            
        elif event_type == "payment.failed":
            payment_id = data.get("id")
            # TODO: Handle failed payment
            print(f"TrySpeed payment failed: {payment_id}")
            
        elif event_type == "payment.expired":
            payment_id = data.get("id")
            # TODO: Handle expired payment
            print(f"TrySpeed payment expired: {payment_id}")
        
        return {"status": "success"}
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SUBSCRIPTION STATUS
# =============================================================================

@router.get("/status/{user_id}")
async def get_subscription_status(user_id: str):
    """
    Get subscription status for a user.
    
    Returns tier and subscription details.
    """
    # TODO: Query database for subscription status
    # For now, return free tier
    
    return {
        "user_id": user_id,
        "tier": "free",
        "subscription": None,
        "message": "Premium features coming soon! All tools are currently free.",
    }

