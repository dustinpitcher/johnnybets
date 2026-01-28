/**
 * NextAuth.js Configuration
 * 
 * Currently enabled:
 * - Email/Password (Credentials) with database persistence
 * 
 * Future providers (uncomment when API keys are ready):
 * - Apple Sign In
 * - Google Sign In
 * - Facebook/Meta Sign In
 * - X (Twitter) Sign In
 * - Email Magic Link (Passwordless)
 */
import { NextAuthOptions } from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';
import prisma from './db';
// import AppleProvider from 'next-auth/providers/apple';
// import GoogleProvider from 'next-auth/providers/google';
// import FacebookProvider from 'next-auth/providers/facebook';
// import TwitterProvider from 'next-auth/providers/twitter';
// import EmailProvider from 'next-auth/providers/email';

// Helper to hash passwords (simple for dev, use bcrypt in production)
function simpleHash(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return hash.toString(16);
}

export const authOptions: NextAuthOptions = {
  // adapter: PrismaAdapter(prisma), // Uncomment when PostgreSQL is ready
  
  providers: [
    // Email/Password Authentication
    CredentialsProvider({
      id: 'credentials',
      name: 'Email',
      credentials: {
        email: { label: 'Email', type: 'email', placeholder: 'you@example.com' },
        password: { label: 'Password', type: 'password' },
        action: { label: 'Action', type: 'text' }, // 'signin' or 'signup'
        inviteCode: { label: 'Invite Code', type: 'text' }, // Required for signup
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          throw new Error('Email and password required');
        }

        const email = credentials.email.toLowerCase().trim();
        const passwordHash = simpleHash(credentials.password);
        const isSignUp = credentials.action === 'signup';

        if (isSignUp) {
          // Require invite code for signup
          if (!credentials.inviteCode) {
            throw new Error('Invite code required to create an account');
          }

          const inviteCodeValue = credentials.inviteCode.trim().toUpperCase();

          // Validate invite code
          const inviteCode = await prisma.inviteCode.findUnique({
            where: { code: inviteCodeValue },
          });

          if (!inviteCode) {
            throw new Error('Invalid invite code');
          }

          if (inviteCode.expiresAt && new Date() > inviteCode.expiresAt) {
            throw new Error('This invite code has expired');
          }

          if (inviteCode.useCount >= inviteCode.maxUses) {
            throw new Error('This invite code has reached its usage limit');
          }

          // Check if user already exists in database
          const existingUser = await prisma.user.findUnique({
            where: { email },
          });
          
          if (existingUser) {
            throw new Error('Account already exists. Please sign in.');
          }

          // Create new user with invite code link
          // Note: We store password hash in the image field temporarily
          // In production, add a proper password field to the User model
          const newUser = await prisma.user.create({
            data: {
              email,
              name: email.split('@')[0],
              // Store password hash - in production, add a dedicated password column
              image: passwordHash, // Temporary: using image field for password hash
              inviteCodeId: inviteCode.id,
            },
          });

          // Increment invite code use count
          await prisma.inviteCode.update({
            where: { id: inviteCode.id },
            data: { useCount: { increment: 1 } },
          });
          
          console.log(`New user created with invite code: ${email} (ID: ${newUser.id}, Invite: ${inviteCodeValue})`);
          
          return {
            id: newUser.id,
            email: newUser.email,
            name: newUser.name,
          };
        } else {
          // Sign in - check credentials in database
          const user = await prisma.user.findUnique({
            where: { email },
          });
          
          if (!user) {
            throw new Error('No account found. Please sign up first.');
          }

          // Check password (stored in image field temporarily)
          if (user.image !== passwordHash) {
            throw new Error('Invalid password');
          }

          return {
            id: user.id,
            email: user.email,
            name: user.name,
          };
        }
      },
    }),

    // === OAuth Providers (uncomment when API keys are configured) ===
    
    // AppleProvider({
    //   clientId: process.env.APPLE_ID!,
    //   clientSecret: process.env.APPLE_SECRET!,
    // }),
    
    // GoogleProvider({
    //   clientId: process.env.GOOGLE_CLIENT_ID!,
    //   clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    // }),
    
    // FacebookProvider({
    //   clientId: process.env.FACEBOOK_CLIENT_ID!,
    //   clientSecret: process.env.FACEBOOK_CLIENT_SECRET!,
    // }),
    
    // TwitterProvider({
    //   clientId: process.env.TWITTER_CLIENT_ID!,
    //   clientSecret: process.env.TWITTER_CLIENT_SECRET!,
    //   version: '2.0',
    // }),
    
    // EmailProvider({
    //   server: {
    //     host: process.env.EMAIL_SERVER_HOST,
    //     port: Number(process.env.EMAIL_SERVER_PORT),
    //     auth: {
    //       user: process.env.EMAIL_SERVER_USER,
    //       pass: process.env.EMAIL_SERVER_PASSWORD,
    //     },
    //   },
    //   from: process.env.EMAIL_FROM || 'JohnnyBets <noreply@johnnybets.com>',
    // }),
  ],
  
  // Session configuration
  session: {
    strategy: 'jwt',
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  
  // JWT configuration
  jwt: {
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  
  // Pages customization
  pages: {
    signIn: '/auth/signin',
    signOut: '/auth/signout',
    error: '/auth/error',
  },
  
  // Callbacks
  callbacks: {
    async signIn({ user, account, profile }) {
      return true;
    },
    
    async redirect({ url, baseUrl }) {
      if (url.startsWith('/')) return `${baseUrl}${url}`;
      if (new URL(url).origin === baseUrl) return url;
      return baseUrl;
    },
    
    async session({ session, token }) {
      // Use our custom id field, falling back to sub
      if (token?.id) {
        session.user.id = token.id as string;
      } else if (token?.sub) {
        session.user.id = token.sub;
      }
      session.user.tier = 'free';
      session.user.role = (token?.role as 'user' | 'admin') || 'user';
      console.log('[Auth] Session callback - user.id:', session.user.id, 'role:', session.user.role);
      return session;
    },
    
    async jwt({ token, user, trigger }) {
      if (user) {
        // Store the database user ID in token.id
        token.id = user.id;
        // Also set sub to match
        token.sub = user.id;
        console.log('[Auth] JWT callback - setting token.id/sub:', user.id);
      }
      
      // Fetch role from database on initial sign in or token refresh
      if (token?.id && (user || trigger === 'update')) {
        const dbUser = await prisma.user.findUnique({
          where: { id: token.id as string },
          select: { role: true },
        });
        token.role = dbUser?.role || 'user';
      } else if (!token.role) {
        // Fetch role if not already in token
        if (token?.id) {
          const dbUser = await prisma.user.findUnique({
            where: { id: token.id as string },
            select: { role: true },
          });
          token.role = dbUser?.role || 'user';
        }
      }
      
      return token;
    },
  },
  
  // Debug mode
  debug: process.env.NODE_ENV === 'development',
};

// Type augmentation for session
declare module 'next-auth' {
  interface Session {
    user: {
      id: string;
      name?: string | null;
      email?: string | null;
      image?: string | null;
      tier: 'free' | 'pro' | 'enterprise';
      role: 'user' | 'admin';
    };
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    id?: string;
    role?: string;
  }
}
