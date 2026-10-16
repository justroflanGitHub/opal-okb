
/* WARNING: Instruction at (ram,0x0001479d) overlaps instruction at (ram,0x0001479b)
    */

void __cdecl16far FUN_144d_02b8(void)

{
  code *pcVar1;
  undefined2 extraout_DX;
  undefined2 extraout_DX_00;
  undefined1 *unaff_SI;
  int unaff_DI;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  bool bVar2;
  undefined1 uVar3;
  char cVar4;
  char cVar5;
  char acStack_bbc [2982];
  undefined1 auStack_e [8];
  uint local_6;
  uint local_4;
  
  cVar5 = SBORROW2((int)&stack0xfffe,0xc);
  cVar4 = (int)auStack_e < 0;
  bVar2 = &stack0x0000 == (undefined1 *)0xe;
  pcVar1 = (code *)swi(0x35);
  (*pcVar1)();
  do {
  } while (bVar2 || cVar5 != cVar4);
  while( true ) {
    pcVar1 = (code *)swi(0x3d);
    (*pcVar1)();
    cVar5 = '\0';
    local_6 = local_4 | 0xc00;
    cVar4 = (int)local_6 < 0;
    uVar3 = (byte)((byte)(local_4 >> 8) | 0xc) == 0;
    pcVar1 = (code *)swi(0x35);
    (*pcVar1)();
    out(*unaff_SI,extraout_DX);
    pcVar1 = (code *)swi(0x3b);
    (*pcVar1)();
    if (!(bool)uVar3 && cVar5 == cVar4) break;
    unaff_SI = unaff_SI + 2;
  }
  pcVar1 = (code *)swi(0x35);
  (*pcVar1)();
  out(unaff_SI[1],extraout_DX_00);
  acStack_bbc[unaff_DI] = acStack_bbc[unaff_DI] + -1;
  return;
}

