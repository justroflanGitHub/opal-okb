
uint __cdecl16near FUN_144d_163a(void)

{
  int iVar1;
  uint in_DX;
  uint uVar2;
  int unaff_BP;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  
  uVar2 = 0xf0;
  if (0xf0 < *(uint *)(unaff_BP + 6)) {
    uVar2 = *(int *)(unaff_BP + 6) + 1U & 0xfffe;
  }
  *(uint *)(unaff_BP + -2) = uVar2;
  uVar2 = FUN_144d_19a8(2,uVar2 + 0xe,0,0);
  if (in_DX != 0xffff) {
    LOCK();
    uVar2 = *(uint *)0x5b0;
    *(uint *)0x5b0 = in_DX;
    UNLOCK();
    *(uint *)0x5b2 = in_DX;
    if (*(uint *)0x5b6 < in_DX) {
      *(uint *)0x5b6 = in_DX;
    }
    if (uVar2 != 0) {
      *(uint *)0x8 = in_DX;
    }
    iVar1 = *(int *)(unaff_BP + -2);
    *(undefined2 *)0x8 = 0;
    *(undefined2 *)(iVar1 + 0xc) = 0xfffe;
    *(undefined2 *)0x0 = 10;
    *(undefined2 *)0x2 = 10;
    *(int *)0xa = iVar1 + 1;
    *(int *)0x6 = iVar1 + 0xe;
    uVar2 = in_DX;
  }
  return uVar2;
}

